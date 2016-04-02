function PromenadeStandardPropertyFactory(ParlayData) {
    
    function PromenadeStandardProperty(data, item_name, protocol) {
        
        this.type = "property";
        
        this.name = data.NAME;
        this.input = data.INPUT;
        this.read_only = data.READ_ONLY;

        // Holds internal value in the constructor closure scope.
        var internal_value;

        // Holds callbacks that are invoked on every value change.
        var onChangeCallbacks = {};

        // defineProperty so that we can define a custom setter to allow us to do the onChange callbacks.
        Object.defineProperty(this, "value", {
            writeable: true,
            get: function () {
                return internal_value;
            },
            set: function (new_value) {
                internal_value = new_value;
                Object.keys(onChangeCallbacks).forEach(function (key) {
                    onChangeCallbacks[key](internal_value);
                });
            }
        });

        /**
         * Allows for callbacks to be registered, these will be invoked on change of value.
         * @param {Function} callback - Function to be invoked whenever the value attribute changes.
         * @returns {Function} - onChange deregistration function.
         */
        this.onChange = function (callback) {
            var UID = 0;
            var keys = Object.keys(onChangeCallbacks);
            while (keys.indexOf(UID) !== -1) {
                UID++;
            }
            onChangeCallbacks[UID] = callback;

            return function deregister() {
                delete onChangeCallbacks[UID];
            };
        };

        this.item_name = item_name;
        this.protocol = protocol;

        this.get = function () {
            return protocol.sendMessage({
                TX_TYPE: "DIRECT",
                MSG_TYPE: "PROPERTY",
                TO: this.item_name
            },
            {
                PROPERTY: this.name,
                ACTION: "GET",
                VALUE: null
            },
            {
                TX_TYPE: "DIRECT",
                MSG_TYPE: "RESPONSE",
                FROM: this.item_name,
                TO: "UI"
            }, true).then(function(response) {
                this.value = response.CONTENTS.VALUE;
                return response;
            }.bind(this));
        };

        this.set = function () {
            return protocol.sendMessage({
                TX_TYPE: "DIRECT",
                MSG_TYPE: "PROPERTY",
                TO: this.item_name
            },
            {
                PROPERTY: this.name,
                ACTION: "SET",
                VALUE: this.value
            },
            {
                TX_TYPE: "DIRECT",
                MSG_TYPE: "RESPONSE",
                FROM: this.item_name,
                TO: "UI"
            }, true);
        };

        ParlayData.set(this.name, this);
        
    }

    return PromenadeStandardProperty;
}

angular.module("promenade.items.property", ["parlay.data"])
    .factory("PromenadeStandardProperty", ["ParlayData", PromenadeStandardPropertyFactory]);