/* XMRig
 * Copyright (c) 2018-2022 SChernykh   <https://github.com/SChernykh>
 * Copyright (c) 2016-2022 XMRig       <https://github.com/xmrig>, <support@xmrig.com>
 * Copyright (c) 2022      grb         <https://github.com/gavinbarnard>
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

#ifndef P2POOLER_VERSION_H
#define P2POOLER_H

#define APP_ID        "p2pooler"
#define APP_NAME      "p2pooler"
#define APP_DESC      "p2pooler a pool that sits ontop of a p2pool chain"
#define APP_VERSION   "0.1"
#define APP_DOMAIN    "pool.aterx.com"
#define APP_SITE      "pool.aterx.com"
#define APP_COPYRIGHT "Copyright (C) 2016-2022 xmrig.com Copyright (C) 2022 aterx.com"
#define APP_KIND      "pool"

#define APP_VER_MAJOR  0
#define APP_VER_MINOR  1
#define APP_VER_PATCH  0

#ifdef _MSC_VER
#   if (_MSC_VER >= 1920)
#       define MSVC_VERSION 2019
#   elif (_MSC_VER >= 1910 && _MSC_VER < 1920)
#       define MSVC_VERSION 2017
#   elif _MSC_VER == 1900
#       define MSVC_VERSION 2015
#   elif _MSC_VER == 1800
#       define MSVC_VERSION 2013
#   elif _MSC_VER == 1700
#       define MSVC_VERSION 2012
#   elif _MSC_VER == 1600
#       define MSVC_VERSION 2010
#   else
#       define MSVC_VERSION 0
#   endif
#endif

#endif /* P2POOLER_VERSION_H */
