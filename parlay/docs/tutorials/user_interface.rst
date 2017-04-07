==============
User Interface
==============

The Parlay User Interface (UI) is a simple and powerful tool used to visualize and interact with your Parlay Items.
The UI is comprised of a workspace where you can add Item or widget Cards, and organize them by dragging and dropping
each card.


Items
-----

The items scripted in Python or connected to Parlay via a custom protocol can be added to the workspace.  By default,
a Parlay discovery request is made to the broker system (Parlay Connect).  After the discovery completes, all of your
items will be made available to add into the workspace.

Adding Items into the Workspace
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Clicking the items menu option in the left side navigator will pull open a library of available items.  At the top most
part of the library, there is a search bar where you can filter your Items by name or ID.  Recall from the
:doc:`hello_world` tutorial that clicking any of the items in the library will launch an item card into the workspace.

If the item is hierarchical, you will be able to expand the item and view its children items by clicking the chevron
icon on the right hand side of the item's displayed name/id.

.. image:: images/parlay_hierarchical_items.png
   :alt: Parlay Item Hierarchy

After you have launched an item into the workspace, multiple functions of the item can be used. On each item card you
will see a few tabs:
-  Commands
-  Property
-  Graph
-  Log

Commands
~~~~~~~~

The command tab allows you to send commands to the Parlay Item, as well as view the response.  You can select different
commands from the command drop down menu underneath the tab selectors.  If you recall from the :doc:`hello_world`
tutorial, clicking the send button underneath the selected command will send the command to the Parlay system and return
the response in the Response Contents section of the command tab.

Whenever the command selected changes, the contents of the script builder will also change. On the Script Builder
toolbar you will see three buttons. The most useful button in this section is the middle button, which will create a
button widget and copy the script and attach it to the button's click event handler.

.. image:: images/parlay_item_script_prompt.png
   :alt: Parlay Item Script Prompt

.. image:: images/parlay_item_script_widget.png
   :alt: Parlay Item Script Widget

.. image:: images/parlay_item_script.png
   :alt: Parlay Item Script Widget with attached script


Widgets
-------

