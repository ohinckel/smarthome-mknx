# SQLite

Configuration
=============

plugin.conf
-----------
<pre>
[sql]
    class_name = SQL
    class_path = plugins.sqlite
#   path = None
#   dumpfile = /tmp/smarthomedb.dump
#   register =  _single : db | _series : series
</pre>

### path
This attribute allows you to specify the directory of the SQLite database if
you do not want to use the default directory.

### dumpfile
If you specify a `dumpfile`, SmartHome.py dumps the database every night into this file.

### register
Usually this plugin registers function on all items to provide access to the
data (see below for the details of the function).

This functions can be used in other plugins or logics or other code you're
using. Since it registers the function on a specific name, you're not able
to use other plugins, which registers functions with the same name too (e.g.
the SQLite plugin).

To avoid naming clashes you can use this configuration setting to register
the function with another name. To configure this use a hash-map style
configuration which consits of the original function name and the mapped
function. The standard configuration is shown above in the example (so no
special mapping is configured).

For example you can configure the registration the function with other names:
<pre>
  register = \_single : sqlite_db | \_series : sqlite_series
</pre>

This will register the `_single` function (as shown below) with another name
`sqlite_db` and the function `_series` (internally used in the visu plugin)
with the name `sqlite_series`. You do not need to specify both if you only
want to use another name for one of the function.

Keep in mind, if you change this, you also need to adjust the code using
the functions with the standard name. On the other hand, this enables you
to use both the `sqlite` and the `rrd` plugin, which currently supports
this.


items.conf
--------------

For num and bool items, you could set the attribute: `sqlite`. By this you enable logging of the item values and SmartHome.py set the item to the last know value at start up (equal cache = yes).

<pre>
[outside]
    name = Outside
    [[temperature]]
        name = Temperatur
        type = num
        sqlite = yes
</pre>


# Functions
This plugin adds one item method to every item which has sqlite enabled.

## cleanup()
This function removes orphaned item entries which are no longer referenced in the item configuration.

## dump(filename)
Dumps the database into the specified file.
`sh.sql.dump('/tmp/smarthomedb.dump')` writes the database content into /tmp/smarthomedb.dump

## move(old, new)
This function renames item entries.
`sh.sql.move('my.old.item', 'my.new.item')`

## sh.item.db(function, start, end='now')
This method returns you an value for the specified function and timeframe.

Supported functions are:

   * `avg`: for the average value
   * `max`: for the maximum value
   * `min`: for the minimum value
   * `on`: percentage (as float from 0.00 to 1.00) where the value has been greater than 0.

For the timeframe you have to specify a start point and a optional end point. By default it ends 'now'.
The time point could be specified with `<number><interval>`, where interval could be:

   * `i`: minute
   * `h`: hour
   * `d`: day
   * `w`: week
   + `m`: month
   * `y`: year

e.g.
<pre>
sh.outside.temperature.db('min', '1d')  # returns the minimum temperature within the last day
sh.outside.temperature.db('avg', '2w', '1w')  # returns the average temperature of the week before last week
</pre>
