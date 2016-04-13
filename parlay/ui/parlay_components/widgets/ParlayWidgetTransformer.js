function ParlayWidgetTransformerFactory() {

    function constructInterpreter(functionString, items) {
        "use strict";

        var initFunc = function (interpreter, scope) {
            if (!!items && items.length > 0) {
                items.forEach(function (item) {

                    var property_value;

                    if (item.type == "input") {
                        property_value = interpreter.createPrimitive(item.element.type == "number" ? parseInt(item.element.value, 10) : item.element.value);
                    }
                    else if (item.type == "button") {
                        // Do something?
                    }
                    else {
                        property_value = interpreter.createPrimitive(item.value);
                    }

                    interpreter.setProperty(scope, item.name, property_value);
                });
            }
        };

        return new Interpreter(functionString, initFunc);
    }

    function runInterpreter(interpreter) {
        interpreter.run();
        return interpreter.value.data;
    }

    function evaluate(functionString, items) {
        "use strict";
        try {
            var interpreter = constructInterpreter(functionString, items);
            return runInterpreter(interpreter);
        }
        catch (error) {
            return error.toString();
        }
    }

    function ParlayWidgetTransformer(initialItems) {
        "use strict";

        // Cache the evaluated value so we aren't creating an Interpreter instance for every access.
        // The cached value will be updated whenever the state of the transformer is altered.
        var cached_value;
        Object.defineProperty(this, "value", {
            get: function () {
                return cached_value;
            }
        });

        this.updateCachedValue = function () {
            cached_value = evaluate(this.functionString, this.items.map(function (container) {
                return container.item;
            }));
        };

        var cached_functionString;
        Object.defineProperty(this, "functionString", {
            get: function () {
                return cached_functionString;
            },
            set: function (value) {
                cached_functionString = value;
                this.updateCachedValue();
            }.bind(this)
        });

        this.items = [];

        if (!!initialItems) {
            initialItems.forEach(this.addItem);
        }
        
    }

    ParlayWidgetTransformer.prototype.cleanHandlers = function () {
        while (!!this.items && this.items.length > 0) {
            this.items.shift().handler();
        }
    };

    ParlayWidgetTransformer.prototype.registerHandler = function (item) {
        if (item.type == "input") {

            item.element.addEventListener("change", this.updateCachedValue.bind(this));

            return function () {
                item.element.removeEventListener("change", this.updateCachedValue);
            }.bind(this);
        }
        else {
            return item.onChange(this.updateCachedValue.bind(this));
        }
    };

    ParlayWidgetTransformer.prototype.addItem = function (item) {
        this.items.push({
            item: item,
            handler: this.registerHandler(item)
        });
    };

    ParlayWidgetTransformer.prototype.removeItem = function (item) {
        var index = this.items.findIndex(function (candidate) {
            return item == candidate.item;
        });

        if (index >= 0) {
            this.items[index].handler();
            this.items.splice(index, 1);
        }
    };

    return ParlayWidgetTransformer;
}

angular.module("parlay.widget.transformer", [])
    .factory("ParlayWidgetTransformer", [ParlayWidgetTransformerFactory]);