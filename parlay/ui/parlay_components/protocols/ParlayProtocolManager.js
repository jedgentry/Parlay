function ParlayProtocolManagerFactory($injector, $q, PromenadeBroker, parlayStore, ParlayNotification) {
    "use strict";

    function ParlayProtocolManager() {

        var open_protocols = [];
        var available_protocols = [];
        var saved_protocols = [];

        /**
         * Requests the Broker to close a protocol.
         * @param {Object} protocol - The protocol to be closed
         * @returns {$q.defer.promise} Resolved when the Broker responds with the close result.
         */
        this.closeProtocol = function (protocol) {
            return PromenadeBroker.closeProtocol(protocol.getName()).then(function (response) {
                // Search for open protocol requested to be closed.
                var index = open_protocols
                    .findIndex(function (suspect) { return protocol.getName() === suspect.getName(); });

                // Remove if we find the protocol, then call it"s onClose method.
                /* istanbul ignore else */
                if (index > -1) open_protocols.splice(index, 1)[0].onClose();

                ParlayNotification.show({content: "Closed " + protocol.getName() + "."});

                return response;
            }).catch(function (status) {
                ParlayNotification.show({content: status});
                return $q.reject(status);
            });
        };

        this.requestDiscovery = function () {
            return PromenadeBroker.requestDiscovery(true);
        };

        /**
         * Delete the protocol configuration in the ParlayStore.
         * @param {Object} configuration - Protocol configuration that we are removing from the ParlayStore.
         */
        this.deleteProtocolConfiguration = function (configuration) {
            var protocols = parlayStore("protocols").getLocalItem("saved");
            if (protocols === undefined) return;

            delete protocols[configuration.name];

            parlayStore("protocols").setLocalItem("saved", protocols);
            setSavedProtocols(parlayStore("protocols").getLocalItem("saved"));
        };

        /**
         * Requests the Broker to open a protocol.
         * Saves the configuration in ParlayStore for later ease of use.
         * @param {Object} configuration - Contains protocol configuration parameters.
         * @returns {$q.defer.promise} - Resolved when the Broker responds with the open result.
         */
        this.openProtocol = function (configuration) {
            return PromenadeBroker.openProtocol(configuration).then(function (response) {
                saveProtocolConfiguration(configuration);
                /* istanbul ignore next */
                ParlayNotification.show({
                    content: "Connected to " + response.name + ".",
                    action: {
                        text: "Discover",
                        callback: function () { this.requestDiscovery(true); }
                    }
                });
                return response;
            }).catch(function (status) {
                ParlayNotification.show({content: status});
                return $q.reject(status);
            });
        };

        /**
         * Returns cached available protocols.
         * @returns {Array} - available protocols.
         */
        this.getAvailableProtocols = function() {
            return available_protocols;
        };

        /**
         * Returns cached open protocols.
         * @returns {Array} - open protocols.
         */
        this.getOpenProtocols = function () {
            return open_protocols;
        };

        /**
         * Returns saved protocol configurations that are available and not currently connected.
         * @returns {Array} - Array of protocol configurations.
         */
        this.getSavedProtocols = function () {
            return saved_protocols;
        };

        /**
         * Clears open and available protocols.
         */
        function clearProtocols() {
            open_protocols.forEach(function (protocol) { protocol.onClose(); });
            open_protocols = [];
            available_protocols = [];
        }

        /**
         * Requests both available and open protocols.
         * @returns {$q.defer.promise} - Resolved when both request responses are received.
         */
        function requestProtocols() {
            return $q.all([requestAvailableProtocols(), requestOpenProtocols()]);
        }

        /**
         * Requests available protocols.
         * @returns {$q.defer.promise} - Resolved when request response is recieved.
         */
        function requestAvailableProtocols() {
            return PromenadeBroker.requestAvailableProtocols();
        }

        /**
         * Requests open protocols.
         * @returns {$q.defer.promise} - Resolved when request response is recieved.
         */
        function requestOpenProtocols() {
            return PromenadeBroker.requestOpenProtocols();
        }

        /**
         * Return a open protocol with the given name.
         * @returns {Object} - Returns Protocol object.
         */
        function getOpenProtocol(name) {
            return open_protocols
                .find(function (protocol) { return name === protocol.getName(); });
        }

        /**
         * Sets private attribute available to an Array of available protocols.
         * @param {Object} protocols - Map of protocol names : protocol details.
         */
        function setAvailableProtocols(protocols) {
            available_protocols = Object.keys(protocols).map(function (protocol_name) {
                return {
                    name: protocol_name,
                    parameters: protocols[protocol_name].params.reduce(function (param_obj, current_param) {
                        param_obj[current_param] = {
                            value: null,
                            defaults: protocols[protocol_name].defaults[current_param]
                        };
                        return param_obj;
                    }, {})
                };
            });
        }

        /**
         * Construct and instantiate a protocol with the given configuration.
         * @param {Object} configuration - Protocol configuration information.
         */
        function openPrototcol (configuration) {
            var Constructor = $injector.has(configuration.protocol_type) ?
                $injector.get(configuration.protocol_type) : $injector.get("PromenadeDirectMessageProtocol");
            var instance = new Constructor(configuration);
            instance.onOpen();
            return instance;
        }

        /**
         * Instantiates and opens the given Array of protocol configurations.
         * @param {Array} protocols - Array of open protocols.
         */
        function setOpenProtocols(protocols) {
            open_protocols = protocols.map(openPrototcol);
        }

        /**
         * Checks to see if a protocol given protocol is available but not currently open.
         * @param {Object} configuration - Object containing protocol configuration details.
         * @returns {Boolean} - True if protocol is available and not currently open.
         */
        function checkSavedConfiguration(configuration) {
            return available_protocols.some(function (protocol) {
                return configuration.name === protocol.name;
            }) && !open_protocols.some(function (protocol) {
                return Object.keys(configuration.parameters).map(function (key) {
                    return configuration.parameters[key];
                }).some(function (value) {
                    return protocol.protocol_name.indexOf(value) !== -1;
                });
            });
        }

        /**
         * Sets the saved_protocols Array if a protocol is available.
         * @param {Object} saved_configurations - Container of saved protocols configurations.
         */
        function setSavedProtocols (saved_configurations) {
            if (saved === undefined) return;

            // Only show saved configurations that are currently available but not connected.
            saved_protocols = Object.keys(saved_configurations)
                .map(function (key) { return saved_configurations[key]; })
                .filter(checkSavedConfiguration);
        }

        /**
         * Adds information from discovery to open Protocol instance.
         * @param {Object} info - Discovery information which may be vendor specific.
         */
        function addDiscoveryInfoToOpenProtocol(info) {
            var protocol = getOpenProtocol(info.NAME);
            if (protocol) protocol.addDiscoveryInfo(info);
        }

        /**
         * Save the protocol configuration in the ParlayStore.
         * @param {Object} configuration - Protocol configuration that can be sent to the Broker.
         */
        function saveProtocolConfiguration(configuration) {
            var protocols = parlayStore("protocols").getLocalItem("saved");
            if (protocols === undefined) protocols = {};

            configuration.last_connected = new Date();

            protocols[configuration.name] = configuration;

            parlayStore("protocols").setLocalItem("saved", protocols);
            setSavedProtocols();
        }

        /**
         * PromenadeBroker callback registrations.
         */

        PromenadeBroker.onOpen(requestProtocols);

        PromenadeBroker.onClose(clearProtocols);

        PromenadeBroker.onMessage({type: "broker", response: "open_protocol_response"}, requestOpenProtocols);

        PromenadeBroker.onMessage({type: "broker", response: "close_protocol_response"}, requestOpenProtocols);

        PromenadeBroker.onMessage({type: "broker", response: "get_protocols_response"}, setAvailableProtocols);

        PromenadeBroker.onMessage({type: "broker", response: "get_open_protocols_response"}, function (response) {
            setOpenProtocols(response.protocols);
            setSavedProtocols(parlayStore("protocols").getLocalItem("saved"));
        });

        PromenadeBroker.onDiscovery(function (response) {
            response.discovery.forEach(addDiscoveryInfoToOpenProtocol);
        });

    }

    return new ParlayProtocolManager();

}

angular.module("parlay.protocols.manager", ["promenade.broker", "promenade.protocols.directmessage", "parlay.notification"])
	.factory("ParlayProtocolManager", ["$injector", "$q", "PromenadeBroker", "ParlayStore", "ParlayNotification", ParlayProtocolManagerFactory]);