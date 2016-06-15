=================================================
Parlay Standard Item Communications Specification
=================================================

Parlay Standard Items are the most commonly used item type in the Parlay
system. They support the *Command* *Streamable* and *Property* interfaces out of
the box, and come with an intuitive automatic UI card in the UI. It is
recommended that most items be sub-classed from the Parlay Standard
Item.

JSON Message Format
===================

All Parlay-defined keys are in CAPS. All custom keys are not.

All Parlay messages are JSON objects with two top-level keys:
 * "TOPICS"
 * "CONTENTS"

The value of each of these is a JSON object.

Topics Object
-------------

The Parlay-defined keys of the "TOPICS" object are as follows:

+-------------+------------+---------------------------------------------------+
| Key         | Required?  | Values                                            |
+=============+============+===================================================+
| "TX\_TYPE"  | Yes        | "DIRECT" or "BROADCAST"                           |
+-------------+------------+---------------------------------------------------+
| "MSG\_TYPE" | Yes        | "COMMAND", "EVENT", "RESPONSE", "PROPERTY", or    |
|             |            | "STREAM"                                          |
+-------------+------------+---------------------------------------------------+
| "RESPONSE\_ | No         | Whether the sender requires a response to this    |
| REQ"        | (default   | message. true or false                            |
|             | false)     |                                                   |
+-------------+------------+---------------------------------------------------+
| "MSG\_ID"   | Conditiona | Required only if a response is required           |
|             | l          | ("RESPONSE\_REQ": true). Unique Alpha-Number      |
|             |            | (from sender). A Response to this message will    |
|             |            | use the same number.                              |
+-------------+------------+---------------------------------------------------+
| "MSG\_STATU | No         | See `Valid Values for MSG\_STATUS                 |
| S"          |            | key <#valid-values-for-MSG_STATUS-key>`__ section |
|             |            | below                                             |
+-------------+------------+---------------------------------------------------+
| "FROM"      | Yes        | The ID of the object this is message is from      |
+-------------+------------+---------------------------------------------------+
| "TO"        | Conditiona | For direct messages ("TX\_TYPE": "DIRECT") only.  |
|             | l          | The ID of the object this message is to.          |
+-------------+------------+---------------------------------------------------+

Users can include their own keys in the TOPICS object. Those
user-defined keys will have no effect on the Parlay Standard Item
User Interface card.

Valid Values for MSG\_STATUS key
--------------------------------

The "MSG\_STATUS" key in the "TOPICS" object is used for response or
asynchronous messages. The following values are allowed for the
"MSG\_STATUS" key:

+---------------+----------------------------------------------------------------------------------------------+
| Value         | Description                                                                                  |
+===============+==============================================================================================+
| "ERROR"       | Script will assert, UI will pop up an error.                                                 |
+---------------+----------------------------------------------------------------------------------------------+
| "WARNING"     | UI will pop up a warning. Message on console.                                                |
+---------------+----------------------------------------------------------------------------------------------+
| "INFO"        | No action taken                                                                              |
+---------------+----------------------------------------------------------------------------------------------+
| "OK"          | UI indicates successful completion                                                           |
+---------------+----------------------------------------------------------------------------------------------+
| "PROGRESS"    | Message successfully received, not completed. 0 or more PROGRESS messages can be sent        |
+---------------+----------------------------------------------------------------------------------------------+
Contents Dictionary
-------------------

The other top level key in a Parlay JSON message is "CONTENTS". Most
fields in the "CONTENTS" object are defined the discovery information
provided by the Protocol. However, some fields are required based on the
value of the MSG\_TYPE field in the TOPICS object:

+---------------+--------------+----------+----------------------------------------+
| TOPICS/MSG\_T | CONTENTS Key | Required | Value                                  |
| YPE           |              | ?        |                                        |
+===============+==============+==========+========================================+
| "COMMAND"     | "COMMAND"    | Yes      | Command identifier (string or number)  |
+---------------+--------------+----------+----------------------------------------+
| "COMMAND"     | "COMMAND\_NA | No       | String name of command for display     |
|               | ME"          |          | (default display is the Command        |
|               |              |          | identifier)                            |
+---------------+--------------+----------+----------------------------------------+
| "RESPONSE"    | "STATUS"     | Yes      | Response status identifier (string or  |
|               |              |          | number)                                |
+---------------+--------------+----------+----------------------------------------+
| "RESPONSE"    | "STATUS\_NAM | No       | String name of status for display      |
|               | E"           |          | (default display is the Response       |
|               |              |          | status identifier                      |
+---------------+--------------+----------+----------------------------------------+
| "EVENT"       | "EVENT"      | Yes      | Event identifier (string or number)    |
+---------------+--------------+----------+----------------------------------------+
| "EVENT"       | "EVENT\_NAME | No       | String name of event identifier for    |
|               | "            |          | display (default display is the event  |
|               |              |          | identifier                             |
+---------------+--------------+----------+----------------------------------------+

If a message is "MSG\_TYPE": "EVENT", or "MSG\_TYPE": "RESPONSE" and
"MSG\_STATUS": "ERROR", then the Parlay Standard Item UI can display
other information contained in the following fields:

+-----------------+-------------+-------------------------------------------------+
| Key             | Required?   | Value                                           |
+=================+=============+=================================================+
| "DESCRIPTION"   | No          | String for display of event or error response   |
+-----------------+-------------+-------------------------------------------------+
| "INFO"          | No          | List of additional informational strings        |
+-----------------+-------------+-------------------------------------------------+

Messages with "MSG\_TYPE": "STREAM" have the following fields. See the
Stream interface for more detail.

+------------+-------------+--------------------------------------------+
| Key        | Required?   | Value                                      |
+============+=============+============================================+
| "STREAM"   | Yes         | Stream Name                                |
+------------+-------------+--------------------------------------------+
| "RATE"     | Yes         | Sample Rate in Hz (0 to cancel sampling)   |
+------------+-------------+--------------------------------------------+
| "VALUE"    | Yes         | Current value                              |
+------------+-------------+--------------------------------------------+

Messages with "MSG\_TYPE": "PROPERTY" have the following fields. See the
Property interface for more detail.

+----------------+--------------+------------------------------------------------+
| Key            | Required?    | Value                                          |
+================+==============+================================================+
| "PROPERTY"     | Yes          | Property Name                                  |
+----------------+--------------+------------------------------------------------+
| "ACTION"       | Yes          | "SET", "GET", or "RESPONSE". Errors will be    |
|                |              | handled with MSG\_STATUS topic                 |
+----------------+--------------+------------------------------------------------+
| "VALUE"        | Conditional  | Only required for "ACTION": "SET" or "ACTION": |
|                |              | "RESPONSE" messages. The value to set the      |
|                |              | property to or the value that was retrieved    |
+----------------+--------------+------------------------------------------------+

Item Discovery
==============

Protocols must respond to Discovery requests with Discovery response
messages. The format of a Discovery response message is defined
elsewhere, but it includes a list of Item objects that have the
following format.

Item ID Format
--------------

Item IDs are unicode strings that must be unique within the Parlay System. Uniqueness is not
guaranteed by the Broker, but should be considered a fatal error by any system during discovery.

To ensure Item ID uniqueness, a hierarchical period-separated schema should be used. The first
level should be the specific adapter type (e.g. 'python','Qt', etc). The specific sub-levels are
left to the decision of the implementation, but should be detailed enough to ensure uniqueness and
ease of management.

Some examples of ID:
For an an item in Python: "python.promenade.LIMS" or "python.project_name.Linker"
For an item on an embedded board: "ArmBoard.5.3ad2"


Item Object Format
------------------

+----------------+-------------+-----------------------------------------------+
| Key            | Required?   | Value                                         |
+================+=============+===============================================+
| "ID"           | Yes         | The system wide unique ID of the  endpoint.   |
|                |             | (`See Item ID Format <#item-id-format>`__)    |
+----------------+-------------+-----------------------------------------------+
| "NAME"         | Yes         | name of item                                  |
+----------------+-------------+-----------------------------------------------+
| "TYPE"         | No          | < type of device, e.g.: "Waveform Generator", |
|                |             | "Stepper Motor"... >                          |
+----------------+-------------+-----------------------------------------------+
| "TEMPLATE"     | Yes         | < e.g. ‘sscom/STD\_ITEM’ >                    |
+----------------+-------------+-----------------------------------------------+
| "INTERFACES"   | No          | < list of interfaces that this item supports  |
|                |             | >                                             |
+----------------+-------------+-----------------------------------------------+
| "CHILDREN"     | No          | < list of children Item objects >             |
+----------------+-------------+-----------------------------------------------+
| "DATA\_STREAMS | No          | < list of DataStream objects (`see format     |
| "              |             | below <#datastream-object-format>`__) >       |
+----------------+-------------+-----------------------------------------------+
| "PROPERTIES"   | No          | < list of Property objects (`see format       |
|                |             | below <#property-object-format>`__ >          |
+----------------+-------------+-----------------------------------------------+
| "CONTENT\_FIEL | Yes         | < list of Field objects (`see format          |
| DS"            |             | below <#field-object-format>`__) that         |
|                |             | describe fields that will be in the CONTENTS  |
|                |             | field of messages from this item >            |
+----------------+-------------+-----------------------------------------------+
| "TOPIC\_FIELDS | No          | < list of Field objects (`see format          |
| "              |             | below <#field-object-format>`__) that         |
|                |             | describe fields that will be in the TOPICS    |
|                |             | field of messages from this item >            |
+----------------+-------------+-----------------------------------------------+

Property Object Format
----------------------

+----------------+-------------+-----------------------------------------------+
| Key            | Required?   | Value                                         |
+================+=============+===============================================+
| "NAME"         | Yes         | The property name                             |
+----------------+-------------+-----------------------------------------------+
| "INPUT"        | Yes         | "NUMBER", "STRING", "NUMBERS", "STRINGS",     |
|                |             | "OBJECT", "ARRAY", "DROPDOWN"                 |
+----------------+-------------+-----------------------------------------------+
| "READ\_ONLY"   | No          | Boolean, whether the property is read only,   |
|                |             | defaults to false                             |
+----------------+-------------+-----------------------------------------------+
| "WRITE\_ONLY"  | No          | Boolean, whether the property is write only,  |
|                |             | defaults to false                             |
+----------------+-------------+-----------------------------------------------+

DataStream Object Format
------------------------

+-----------+------------+----------------------------------------------------------------+
| Key       | Required   | Value                                                          |
+===========+============+================================================================+
| "NAME"    | Yes        | The data stream name                                           |
+-----------+------------+----------------------------------------------------------------+
| "UNITS"   | No         | Human readable string representing units of this data stream   |
+-----------+------------+----------------------------------------------------------------+

Field Object format
-------------------

+----------------+-------------+-----------------------------------------------+
| Key            | Required?   | Value                                         |
+================+=============+===============================================+
| "LABEL"        | No          | (label to show same as MSG\_KEY if not        |
|                |             | defined)                                      |
+----------------+-------------+-----------------------------------------------+
| "MSG\_KEY"     | Yes         | < key passed with created message for this    |
|                |             | field >                                       |
+----------------+-------------+-----------------------------------------------+
| "INPUT"        | Yes         | "NUMBER", "STRING", "NUMBERS", "STRINGS",     |
|                |             | "OBJECT", "ARRAY", "DROPDOWN"                 |
+----------------+-------------+-----------------------------------------------+
| "REQUIRED"     | No          | If true, require the user fill out before     |
|                |             | sending command                               |
+----------------+-------------+-----------------------------------------------+
| "DEFAULT"      | No          | Default value for the input. If dropdown,     |
|                |             | then this will be the selected default        |
+----------------+-------------+-----------------------------------------------+
| "HIDDEN"       | No          | If set to true, will hide the input from the  |
|                |             | user (i.e.: The default will be used as the   |
|                |             | value since the user can’t change anything)   |
+----------------+-------------+-----------------------------------------------+
| "DROPDOWN\_OPT | Conditional | If input is a dropdown, must be a list of     |
| IONS"          |             | strings or a list of tuples                   |
+----------------+-------------+-----------------------------------------------+
| "DROPDOWN\_SUB | No          | < list of Field objects>                      |
| \_FIELDS"      |             |                                               |
+----------------+-------------+-----------------------------------------------+
