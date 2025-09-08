/* p2pooler
 * Copyright 2010      Jeff Garzik <jgarzik@pobox.com>
 * Copyright 2012-2014 pooler      <pooler@litecoinpool.org>
 * Copyright 2014      Lucas Jones <https://github.com/lucasjones>
 * Copyright 2014-2016 Wolf9466    <https://github.com/OhGodAPet>
 * Copyright 2016      Jay D Dee   <jayddee246@gmail.com>
 * Copyright 2017-2018 XMR-Stak    <https://github.com/fireice-uk>, <https://github.com/psychocrypt>
 * Copyright 2018-2020 SChernykh   <https://github.com/SChernykh>
 * Copyright 2016-2020 XMRig       <https://github.com/xmrig>, <support@xmrig.com>
 * Copyright 2022      grb         <https://github.com/gavinbarnard>
 *
 *   This program is free software: you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation, either version 3 of the License, or
 *   (at your option) any later version.
 *
 *   This program is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 *   GNU General Public License for more details.
 *
 *   You should have received a copy of the GNU General Public License
 *   along with this program. If not, see <http://www.gnu.org/licenses/>.
 */

#include "proxy/Recorder.h"
#include "base/io/log/Log.h"
#include "base/io/log/Tags.h"
#include "base/net/stratum/SubmitResult.h"
#include "core/config/Config.h"
#include "core/Controller.h"
#include "proxy/events/AcceptEvent.h"
#include "proxy/Miner.h"
#include "base/tools/Chrono.h"
#include <hiredis/hiredis.h>

#include <cinttypes>

#include <stdio.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netdb.h>
#include <cstring>
#include <string>
#include <mutex>

xmrig::Recorder::Recorder(Controller *controller) :
    m_controller(controller)
{
    //sockfd = socket(AF_INET, SOCK_DGRAM, 0);
    //if (sockfd < 0) {
    //    LOG_ERR("sockfd less than 0 %d", sockfd);
    //}
    rdCtx = redisConnect("localhost", 6379);  // FIX ME should load this from a cli option Review -> still deffered 
    if (rdCtx == NULL || rdCtx->err) {
        if (rdCtx) {
            LOG_ERR("Redis connection error: %s",  rdCtx->errstr);
            redisFree(rdCtx);
        } else {
            LOG_ERR("Redis connection error: Can't allocate redis context.");
        }
    }
}


xmrig::Recorder::~Recorder() {
    if (rdCtx) {
        redisFree(rdCtx);
        rdCtx = nullptr;
    }
}

void xmrig::Recorder::onEvent(IEvent *event)
{
    switch (event->type())
    {
    case IEvent::AcceptType:
        accept(static_cast<AcceptEvent*>(event));
        break;

    default:
        break;
    }
}


void xmrig::Recorder::onRejectedEvent(IEvent *event)
{
    switch (event->type())
    {
    case IEvent::AcceptType:
        reject(static_cast<AcceptEvent*>(event));
        break;
    default:
        break;
    }
}

bool xmrig::Recorder::validateAddress(const char *s)
{
    // Check for null pointer
    if (s == nullptr) 
    {
        return false;
    }
    
    // Determine string length
    size_t len = strlen(s);
    
    // Check length requirement (must be exactly 95 characters)
    if (len != 95) 
    {
        return false;
    }
    
    // Check first character is '4' or '8'
    char first_char = s[0];
    if (first_char != '4' && first_char != '8') 
    {
        return false;
    }
    
    // Define allowed Base58 characters
    const std::string allowed_chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
    
    // Precompute an array for O(1) character lookups
    bool allowed[256] = {false};
    for (char c : allowed_chars) {
        allowed[static_cast<unsigned char>(c)] = true;
    }
    
    // Validate each character in the input string
    for (size_t i = 0; i < len; ++i) {
        char current_char = s[i];
        if (!allowed[static_cast<unsigned char>(current_char)]) return false;
    }
    // All checks passed
    return true;
}

void xmrig::Recorder::add_share_to_redis(const char *user, const u_int64_t ts, const u_int64_t diff) 
{
    /*
    REDIS COMMANDS
    
    JSON.ARRAPPEND key path value

    JSON.ARRAPPEND s_{user} $ 'json_string'
    
    JSON.SET key path value

    JSON.SET s_{user} $ '[]'

    */
    char share_key[1024];
    char json_str[512];
    redisReply *reply;
    redisReply *reply_set;
    snprintf(share_key, sizeof(share_key), "s_%s", user);
    snprintf(json_str, sizeof(json_str), "{\"timestamp\":%lu,\"diff\":%lu}", ts, diff);
    const char* JSON_ARRAPPEND = "JSON.ARRAPPEND";
    const char* JSON_SET = "JSON.SET";
    const char* argv_arrappend[] = {JSON_ARRAPPEND, share_key, "$", json_str};
    const char* argv_set[] = {JSON_SET, share_key, "$", "[]"};
    int argc_arrappend = 4;
    int argc_set = 4;
    const size_t argv_arrappen_len[] = {strlen(JSON_ARRAPPEND), strlen(share_key), 1, strlen(json_str)};
    const size_t argv_set_len[] = {strlen(JSON_SET), strlen(share_key), 1, 2};
    std::lock_guard<std::mutex> lock(m_redis_mutex);
    reply = (redisReply *) redisCommandArgv(rdCtx, argc_arrappend, argv_arrappend, argv_arrappen_len);
    if (reply == NULL)
    {
        LOG_ERR("redis Connection error");
    } 
    else if (reply->type == REDIS_REPLY_ERROR) 
    {
        const char* errMsg = reply->str;
        if (strstr(errMsg, "could not perform this operation on a key that doesn't exist")) 
        {
            reply_set = (redisReply *) redisCommandArgv(rdCtx, argc_set, argv_set, argv_set_len);
            if (reply_set == NULL) {
                LOG_ERR("Failed to set NULL");
            } 
            else if (reply_set->type != REDIS_REPLY_STATUS)
            {
                LOG_ERR("Failed to set");
            }
            freeReplyObject(reply_set);
            reply = (redisReply *) redisCommandArgv(rdCtx, argc_arrappend, argv_arrappend, argv_arrappen_len);
            if (reply == NULL)
            {
                LOG_ERR("Failed to append after set NULL");
            } 
            else if (reply->type == REDIS_REPLY_ARRAY)
            {
                LOG_PPLNS("Correctly appended after set");
                LOG_PPLNS("share added user=%s, ts=%" PRIu64", diff=%" PRIu64, user, ts, diff);
            } 
            else 
            {
                LOG_ERR("Failed to append after set");
            }
        }
    } else if (reply->type == REDIS_REPLY_ARRAY) {
        LOG_PPLNS("share added user=%s, ts=%" PRIu64", diff=%" PRIu64, user, ts, diff);
    } else {
        LOG_ERR("share failed user=%s, ts=%" PRIu64", diff=%" PRIu64, user, ts, diff);
    }
}

void xmrig::Recorder::accept(const AcceptEvent *event)
{
    if (event->isDonate() || event->isCustomDiff()) {
        return;
    }
    const char* og_user = event->miner()->user();
    const u_int64_t timestamp = Chrono::currentMSecsSinceEpoch();
    const u_int64_t diff = event->result.diff;
    //LOG_PPLNS("user=%s,ts=%" PRIu64",diff=%" PRIu64, (char*)user, timestamp, diff);

    // new code to remove reliance on another outside daemon (receiver.py)
    // and add into redis in this event
    char buffer_user[1024] = {0};
    char final_user[1024] = {0};
    size_t max_copy_length = sizeof(buffer_user) - 1; 
    std::strncpy(buffer_user, og_user, max_copy_length);
    buffer_user[max_copy_length] = '\0';

    char* plusPos = std::strchr(buffer_user, '+');
    if (plusPos != nullptr) 
    {
        *plusPos = '\0';
    }
    std::strncpy(final_user, buffer_user, strlen(buffer_user)); 
    if (validateAddress(final_user))
    {
        add_share_to_redis(final_user, timestamp, diff);
    }

    /* Original code to send to receiver.py */
    /*
    
    struct hostent *server;
    int portno = 6969;
    struct sockaddr_in serv_addr;
    server = gethostbyname("localhost");
    bzero((char *) &serv_addr, sizeof(serv_addr));
    serv_addr.sin_family = AF_INET;
    bcopy((char *)server->h_addr, 
    (char *)&serv_addr.sin_addr.s_addr, server->h_length);
    serv_addr.sin_port = htons(portno);
    if (sockfd < 0) {
        LOG_ERR("sockfd is dead %d", sockfd);
    } else {
        char message[1024] = {0};
        sprintf(message,"{\"user\":\"%s\",\"ts\": %" PRIu64", \"diff\": %" PRIu64"}", (char*)user, timestamp, diff);
        sendto(sockfd, message, strlen(message), 0, (struct sockaddr *)&serv_addr, sizeof(serv_addr));
    }
    
    */

}

void xmrig::Recorder::reject(const AcceptEvent *event)
{
    if (event->isDonate()) {
        return;
    }
    // should we penalize users for bad shares ?~
}
