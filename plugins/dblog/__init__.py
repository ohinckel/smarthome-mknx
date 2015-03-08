#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
# Copyright 2013 Marcus Popp                               marcus@popp.mx
#########################################################################
#  This file is part of SmartHome.py.    http://mknx.github.io/smarthome/
#
#  SmartHome.py is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHome.py is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHome.py. If not, see <http://www.gnu.org/licenses/>.
#########################################################################

import logging
import datetime
import functools
import time
import threading
import lib.db
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger('')


class DbLog():

    # SQL queries
    # time, item_id, val_str, val_num, val_bool
    _setup = {
      '1' : "CREATE TABLE log (time BIGINT, item_id INTEGER, duration BIGINT, val_str TEXT, val_num REAL, val_bool BOOLEAN);",
      '2' : "CREATE TABLE item (id INTEGER, name varchar(255), time BIGINT, val_str TEXT, val_num REAL, val_bool BOOLEAN);",
      '3' : "CREATE INDEX log_item_id_time ON log (item_id, time);",
      '4' : "CREATE INDEX item_name ON item (name);"
    }

    def __init__(self, smarthome, db, connect, cycle=60):
        self._sh = smarthome
        self._dump_cycle = int(cycle)
        self._buffer = {}
        self._buffer_lock = threading.Lock()
        self._dump_lock = threading.Lock()

        self._db = lib.db.Database("DbLog", self._sh.dbapi(db), connect)
        self._db.connect()
        self._db.setup(self._setup)

        smarthome.scheduler.add('DbLog dump', self._dump, cycle=self._dump_cycle, prio=5)

    def parse_item(self, item):
        if 'dblog' in item.conf:
            self._buffer[item] = []
            item.series = functools.partial(self._series, item=item.id())
            item.db = functools.partial(self._single, item=item.id())
            return self.update_item
        else:
            return None

    def run(self):
        self.alive = True

    def stop(self):
        self.alive = False
        self._dump(True)
        self._db.close()

    def update_item(self, item, caller=None, source=None, dest=None):
        start = self._timestamp(item.prev_change())
        end = self._timestamp(item.last_change())

        t = [start, end - start]
        t.extend(self._item_value_tuple(item.type(), item.prev_value()))

        self._buffer[item].append(tuple(t))

    def _item_value_tuple(self, item_type, item_val):
        if item_type == 'num':
           val_str = None
           val_num = float(item_val)
           val_bool = None
        elif item_type == 'bool':
           val_str = None
           val_num = None
           val_bool = bool(item_val)
        else:
           val_str = str(item_val)
           val_num = None
           val_bool = None

        return [val_str, val_num, val_bool]

    def _datetime(self, ts):
        return datetime.datetime.fromtimestamp(ts / 1000, self._sh.tzinfo())

    def _dump(self, finalize=False, items=None):
        if self._dump_lock.acquire(False) == False:
            logger.debug('Skipping dump, since other dump running!')
            return

        logger.debug('Starting dump')

        if items == None:
            self._buffer_lock.acquire()
            items = list(self._buffer.keys())
            self._buffer_lock.release()

        for item in items:
            self._buffer_lock.acquire()
            tuples = self._buffer[item]
            self._buffer[item] = []
            self._buffer_lock.release()

            if len(tuples) or finalize:

                # Test connectivity
                retry = 5
                while retry > 0:
                    try:
                        self._db.lock()

                        if self._db.connected() == False:
                            self._db.connect()

                        self._db.fetchone("SELECT 1");

                        retry = -1

                    except Exception as e:
                        logger.warning("DbLog: connection error: {}".format(e))
                        self._db.close()
                        retry = retry - 1
                        time.sleep(2)
                    finally:
                        self._db.release()

                if retry == 0:
                    logger.error("DbLog: connection not recovered, skipping dump");
                    self._dump_lock.release()
                    return

                try:
                    self._db.lock()

                    # Create new item ID
                    id = self._db.fetchone("SELECT id FROM item where name = ?;", (item.id(),))
                    if id == None:
                        id = self._db.fetchone("SELECT MAX(id) FROM item;")

                        cur = self._db.cursor()
                        self._db.execute("INSERT INTO item(id, name) VALUES(?,?);", (1 if id[0] == None else id[0]+1, item.id()), cur)
                        id = self._db.fetchone("SELECT id FROM item where name = ?;", (item.id(),), cur)
                        cur.close()

                    id = id[0]

                    # Get current values of item
                    start = self._timestamp(item.last_change())
                    end = self._timestamp(self._sh.now())
                    val = self._item_value_tuple(item.type(), item())

                    # When finalizing (e.g. plugin shutdown) add current value to item and log
                    if finalize:
                        _update = [end]
                        _update.extend(val)
                        _update.append(id)

                        current = [start, end - start]
                        current.extend(val)
                        tuples.append(tuple(current))

                    else:
                        _update = [start]
                        _update.extend(val)
                        _update.append(id)

                    # Dump tuples
                    logger.debug('Dumping {}/{} with {} values'.format(item.id(), id, len(tuples)))

                    cur = self._db.cursor()
                    for t in tuples:
                        _insert = ( t[0], id, t[1], t[2], t[3], t[4] )

                        # time, item_id, duration, val_str, val_num, val_bool
                        self._db.execute("INSERT INTO log VALUES (?,?,?,?,?,?);", _insert, cur)

                    # time, val_str, val_num, val_bool, item_id
                    self._db.execute("UPDATE item SET time = ?, val_str = ?, val_num = ?, val_bool = ? WHERE id = ?;", tuple(_update), cur)

                    cur.close()

                    self._db.commit()
                except Exception as e:
                    logger.warning("DbLog: problem updating {}: {}".format(item.id(), e))
                finally:
                    self._db.release()
        logger.debug('Dump completed')
        self._dump_lock.release()

    def _series(self, func, start, end='now', count=100, ratio=1, update=False, step=None, sid=None, item=None, offset=None):
        init = not update
        if sid is None:
            sid = item + '|' + ((offset + '|') if offset != None else '') + func + '|' + start + '|' + end
        if offset == None:
            offset = "0h"
        istart = self._parse_ts(start)
        iend = self._parse_ts(end)
        ioffset = self._parse_ts(offset, True)
        logger.debug("offset range {} - {}, offset {} ({}) = {}".format(istart, iend, self._parse_ts(offset), offset, ioffset))
        if step is None:
            if count != 0:
                step = int((iend - istart) / count)
            else:
                step = iend - istart
        reply = {'cmd': 'series', 'series': None, 'sid': sid}
        reply['params'] = {'update': True, 'item': item, 'func': func, 'start': iend, 'end': end, 'step': step, 'sid': sid}
        reply['update'] = self._sh.now() + datetime.timedelta(seconds=int(step / 1000))
        where = " FROM log WHERE item_id = ? AND time + duration > ? AND time <= ? GROUP BY ROUND(time / ?)"
        if func == 'avg':
            query = "SELECT MIN(time + " + str(ioffset) + "), ROUND(AVG(val_num * duration) / AVG(duration), 2)" + where + " ORDER BY time ASC"
        elif func == 'min':
            query = "SELECT MIN(time + " + str(ioffset) + "), MIN(val_num)" + where
        elif func == 'max':
            query = "SELECT MIN(time + " + str(ioffset) + "), MAX(val_num)" + where
        elif func == 'on':
            query = "SELECT MIN(time + " + str(ioffset) + "), ROUND(SUM(val_bool * duration) / SUM(duration), 2)" + where + " ORDER BY time ASC"
        else:
            raise NotImplementedError
        _item = self._sh.return_item(item)
        if self._buffer[_item] != []:
            self._dump(items=[_item])
        tuples = self._fetch(query, item, [istart - ioffset, iend - ioffset, step])
        if tuples:
            if istart - ioffset > tuples[0][0]:
                tuples[0] = (istart, tuples[0][1])
            if end != 'now':
                tuples.append((iend, tuples[-1][1]))
        else:
            tuples = []
        item_change = self._timestamp(_item.last_change())
        if item_change < iend - ioffset:
            value = float(_item())
            if item_change < istart - ioffset:
                tuples.append((istart, value))
            elif init:
                tuples.append((item_change, value))
            if init:
                tuples.append((iend, value))
        reply['series'] = tuples
        return reply

    def _single(self, func, start, end='now', item=None):
        start = self._parse_ts(start)
        end = self._parse_ts(end)
        where = " FROM log WHERE item_id = ? AND time + duration > ? AND time <= ?"
        if func == 'avg':
            query = "SELECT ROUND(AVG(val_num * duration) / AVG(duration), 2)" + where
        elif func == 'min':
            query = "SELECT MIN(val_num)" + where
        elif func == 'max':
            query = "SELECT MAX(val_num)" + where
        elif func == 'on':
            query = "SELECT ROUND(SUM(val_bool * duration) / SUM(duration), 2)" + where
        else:
            logger.warning("Unknown export function: {0}".format(func))
            return
        _item = self._sh.return_item(item)
        if self._buffer[_item] != []:
            self._dump(items=[_item])
        tuples = self._fetch(query, item, [start, end])
        if tuples is None:
            return
        return tuples[0][0]

    def _fetch(self, query, item, params):
        self._db.lock()
        try:
            id = self._db.fetchone("SELECT id FROM item where name = ?", (item,))
            params.insert(0, id[0])
            tuples = self._db.fetchall(query, tuple(params))
        except Exception as e:
            logger.warn("DBLog: Error fetching data for {}: {}".format(item, e))
        finally:
            self._db.release()
        if tuples is None:
            return None
        else:
            return list(tuples)

    def _parse_ts(self, frame, offset=False):
        minute = 60 * 1000
        hour = 60 * minute
        day = 24 * hour
        week = 7 * day
        month = 30 * day
        year = 365 * day

        _frames = {'i': minute, 'h': hour, 'd': day, 'w': week, 'm': month, 'y': year}
        try:
            return int(frame)
        except:
            pass
        ts = self._timestamp(self._sh.now())
        if frame == 'now':
            fac = 0
            frame = 0
        elif frame[-1] in _frames:
            fac = _frames[frame[-1]]
            frame = frame[:-1]
        else:
            return frame
        try:
            if offset:
                ts = int(float(frame) * fac)
            else:
                ts = ts - int(float(frame) * fac)
        except:
            logger.warning("DBLog: Unknown time frame '{0}'".format(frame))
        return ts

    def _timestamp(self, dt):
        return int(time.mktime(dt.timetuple())) * 1000 + int(dt.microsecond / 1000)
