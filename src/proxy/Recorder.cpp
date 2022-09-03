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

#include <cinttypes>

#include <stdio.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netdb.h>

xmrig::Recorder::Recorder(Controller *controller) :
    m_controller(controller)
{
    sockfd = socket(AF_INET, SOCK_DGRAM, 0);
    if (sockfd < 0) {
        LOG_ERR("sockfd less than 0 %d", sockfd);
    } 
}


xmrig::Recorder::~Recorder() = default;


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


void xmrig::Recorder::accept(const AcceptEvent *event)
{
    if (event->isDonate() || event->isCustomDiff()) {
        return;
    }
    const char* user = event->miner()->user();
    const u_int64_t timestamp = Chrono::currentMSecsSinceEpoch();
    const u_int64_t diff = event->result.diff;
    LOG_PPLNS("user=%s,ts=%" PRIu64",diff=%" PRIu64, (char*)user, timestamp, diff);
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
}

void xmrig::Recorder::reject(const AcceptEvent *event)
{
    if (event->isDonate()) {
        return;
    }
    // should we penalize users for bad shares ?~
}
