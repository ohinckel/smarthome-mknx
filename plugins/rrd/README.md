# RRDTool

Requirements
============
You have to install the python3 bindings for rrdtool:
<pre>$ sudo apt-get install python3-dev librrd-dev
$ cd lib/3rd/rrdtool
$ sudo python3 setup.py install</pre>

Configuration
=============

Remark: 
-------
The rrd plugin and the sqlite plugin can not be used together. Some pros and cons:

RRD
+ a stable, reliable tool
+ is used in a many data logging and graphing tools
- slow moving development
- only few new features on the roadmap

SQLite
+ part of python, no additional installation necessary
+ accurate logging of changing times
+ more analysis functionality

plugin.conf
-----------
<pre>
[rrd]
    class_name = RRD
    class_path = plugins.rrd
    # step = 300
    # rrd_dir = /usr/smarthome/var/rrd/
    # register = _single : db | _series : series
</pre>

### step
Sets the cycle time how often entries will be updated.

### rrd_dir
Specify the directory of the rrd storage.

### register
Usually this plugin registers function on all items to provide access to the
data (see below for the details of the function).

This functions can be used in other plugins or logics or other code you're
using. Since it registers the function on a specific name, you're not able
to use other plugins, which registers functions with the same name too (e.g.
the SQLite plugin).

To avoid nameing clashes you can use this configuration setting to register
the function with another name. To configure this use a hash-map style
configuration which consits of the original function name and the mapped
function. The standard configuration is shown above in the example (so no
special mapping is configured).

For example you can configure the registration the function with other names:
<pre>
  register = \_single : rrd_db | \_series : rrd_series
</pre>

This will register the `_single` function (as shown below) with another name
`rrd_db` and the function `_series` (internally used in the visu plugin)
with the name `rrd_series`. You do not need to specify both if you only
want to use another name for one of the function.

Keep in mind, if you change this, you also need to adjust the code using
the functions with the standard name. On the other hand, this enables you
to use both the `sqlite` and the `rrd` plugin, which currently supports
this.


items.conf
--------------

### rrd
To active rrd logging (for an item) simply set this attribute to yes.
If you set this attribute to `init`, SmartHome.py tries to set the item to the last known value (like cache = yes).

### rrd_min
Set this item attribute to log the minimum as well. Default is no.

### rrd_max
Set this item attribute to log the maximum as well. Default is no.

### rrd_mode
Set the type of data source. Default ist `gauge`.
  * `gauge` - should be used for things like temperatures.
  * `counter` - should be used for continuous incrementing counters like the Powermeter (kWh), watercounter (m³), pellets (kg).

<pre>
[outside]
    name = Outside
    [[temperature]]
        name = Temperatur
        type = num
        rrd = init
        rrd_min = yes
        rrd_max = yes

[office]
    name = Büro
    [[temperature]]
        name = Temperatur
        type = num
        rrd = yes
</pre>

# Functions
This plugin adds one item method to every item which has rrd enabled.

## sh.item.db(function, start, end='now')
This method returns you a value for the specified function and timeframe.

Supported functions are:

   * `avg`: for the average value
   * `max`: for the maximum value
   * `min`: for the minimum value
   * `last`: for the last value

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

