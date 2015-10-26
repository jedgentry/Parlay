 /**
 * If the buffer is valid and available we should force the md-chips controller to push it to the ng-model.
 * @param {NodeList} chipElements - List of HTMLElements mapping to each md-chip.
 */
function pushChipBuffer (chipElements) {
    if (chipElements.length) {
	    var ctrl = angular.element(chipElements[0].querySelector('input')).scope().$mdChipsCtrl;
	    var buffer = ctrl.getChipBuffer();
	    if (buffer !== "") {
			ctrl.appendChip(buffer);
			ctrl.resetChipBuffer();    
	    }			
	}
}

/**
 * Collects and formats the fields available on the given message object.
 * @param {Object} message - message container from the scope.
 * @returns - parsed and formatted StandardEndpoint data.
 */    
function collectMessage (message) {
    return Object.keys(message).reduce(function (accumulator, field) {
        var param_name, field_type;
        
        if (field.indexOf('_') > -1) {
	        var split_field = field.split('_');

            field_type = split_field[split_field.length - 1];

            param_name = split_field.slice(0, split_field.length - 1).join('_');
	    }
	    else {
		    param_name = field;
	    }
	    
	    // If type is Object or Array then turn the JSON string into an actual Object.
	    if (field_type === "ARRAY") accumulator[param_name] = message[field].map(function (chip) { 
		    return !Number.isNaN(chip.value) ? parseInt(chip.value) : chip.value;
		});
	    else if (field_type === "NUMBERS") accumulator[param_name] = message[field].map(parseFloat);
	    else if (angular.isObject(message[field])) accumulator[param_name] = message[field].value;
        else accumulator[param_name] = message[field];
        
        return accumulator;
    }, {});

}

/**
 * Controller constructor for the command tab.
 * @constructor
 * @param {AngularJS $scope} $scope - A AngularJS $scope Object.
 * @param {AngularJS Service} $timeout - AngularJS timeout service.
 * @param {Parlay Service} ScriptLogger - Parlay ScriptLogger Service.
 * @param {Parlay Service} ParlayUtility - Parlay Utlity Service.
 */
function PromenadeStandardEndpointCardCommandTabController($scope, $timeout, ScriptLogger, ParlayUtility) {
	ParlayBaseTabController.call(this, $scope, "promenadeStandardEndpointCardCommands");
	
	// Due to the way JavaScript prototypical inheritance works and AngularJS scoping we want to enclose the message Object within another object.
	// Reference AngularJS "dot rule": http://jimhoskins.com/2012/12/14/nested-scopes-in-angularjs.html
	$scope.wrapper = {
		message: {}
	};
	
	// Controller attributes that reflect the state of the command form.
	this.error = false;
	this.sending = false;
	this.status_message= null;
	
	// Reference to a $timeout deregistration function.
	var sending_timeout = null;
	
	/**
	 * Collects and sends the command from the form. During this process it will update controller attributes to inform the user the current status.
	 * @param {Event} $event - This event's target is used to reference the md-chips element so that we can clear the buffer if available.
	 */
	this.send = function ($event) {
		// Push the buffer into the md-chips ng-model
		if ($event) pushChipBuffer($event.target.querySelectorAll('md-chips'));
	    
	    this.error = false;
	    this.sending = true;
	    
	    try {
	    	var message = collectMessage($scope.wrapper.message);
	    	this.endpoint.sendMessage(message).then(function (response) {
			     	
			     	// Use the response to display feedback on the send button.
			        this.status_message = response.STATUS_NAME;
			        
			        // If we still have an outstanding timeout we should cancel it to prevent the send button from flickering.
		            if (sending_timeout !== null) $timeout.cancel(sending_timeout);
		            
		            // Setup a timeout to reset the button to it's default state after a brief period of time.
		        	sending_timeout = $timeout(function () {
			        	sending_timeout = null;
		                this.sending = false;
		                this.status_message = null;
		            }, 500);
		            
		        }.bind(this)).catch(function (response) {
			        this.sending = false;
			        this.error = true;
			        this.status_message = response.STATUS_NAME;
		        }.bind(this));
		    
		    // Put the Python equivalent command in the log.
	        ScriptLogger.logCommand("SendCommand(" + Object.keys(message).map(function (key) {
		        return typeof message[key] === 'number' ? key + '=' + message[key] : key + "='" + message[key] + "'";
	        }).join(',') + ')');
	    }
	    catch (e) {
	     	this.error = true;
	     	this.status_message = e;   
	    }
	};
	
	// Watch for new fields to fill with defaults.
    $scope.$watchCollection("wrapper.message", function () {
	    Object.keys($scope.wrapper.message).filter(function (key) {
		    // Build an Array with fields that have sub fields.
		    return $scope.wrapper.message[key] !== undefined && $scope.wrapper.message[key].hasOwnProperty("sub_fields");
	    }).map(function (key) {
	        return $scope.wrapper.message[key].sub_fields;
	    }).reduce(function (accumulator, current) {
		    // Join all the sub_fields into a larger Array.
		    return accumulator.concat(current);
	    }, []).filter(function (field) {
		    // Check if the sub field already has a message field entry.
	        return field !== undefined && !$scope.wrapper.message.hasOwnProperty(field.msg_key + '_' + field.input);
	    }).forEach(function (field) {
		    // Fill in the default value in the message Object.
	        $scope.wrapper.message[field.msg_key + '_' + field.input] = ['NUMBERS', 'STRINGS', 'ARRAY'].indexOf(field.input) > -1 ? [] : field.default;
	    });
    });
	
}

// Prototypically inherit from ParlayBaseTabController.
PromenadeStandardEndpointCardCommandTabController.prototype = Object.create(ParlayBaseTabController.prototype);

/**
 * Directive constructor for PromenadeStandardEndpointCardCommands.
 * @returns {Object} - Directive configuration.
 */
function PromenadeStandardEndpointCardCommands() {
	return {
        scope: {
            endpoint: "="
        },
        templateUrl: "../vendor_components/promenade/endpoints/directives/promenade-standard-endpoint-card-commands.html",
        controller: "PromenadeStandardEndpointCardCommandTabController",
        controllerAs: "ctrl",
        bindToController: true
    };
}

/**
 * Directive constructor for PromenadeStandardEndpointCardCommandContainer.
 * @param {AngularJS Service} RecursionHelper - Allows recursive nesting of this directive within itself for sub field support.
 * @param {Parlay Service} ParlayPersistence - Allows directive to persist values that it should retain between sessions.
 * @param {Parlay Service} ParlayUtility - Parlay Utility Service.
 * @returns {Object} - Directive configuration.
 */
function PromenadeStandardEndpointCardCommandContainer(RecursionHelper, ParlayPersistence, ParlayUtility) {
	return {
        scope: {
            wrapper: '=',
            fields: '=',
            commandform: '='
        },
        templateUrl: '../vendor_components/promenade/endpoints/directives/promenade-standard-endpoint-card-command-container.html',
        compile: RecursionHelper.compile,
        controller: function ($scope) {

	        var container = ParlayUtility.relevantScope($scope, 'container').container;
			var directive_name = 'parlayEndpointCard.' + container.ref.name.replace(' ', '_') + '_' + container.uid;
		    
		    ParlayPersistence(directive_name, "wrapper.message", $scope);
	        
	        /**
		     * Packages $mdChip object for insertion into message.
		     * @param {$mdChip} chip - $mdChip Object
		     */
	        $scope.prepChip = function (chip) {
   			    return {value: chip};
		    };
	        
	        /**
		     * Checks if the given field has sub fields available.
		     * @param {Object} field - the field we are interested in.
		     * @returns {Boolean} - true if the target field has sub fields available, false otherwise.
		     */
	        $scope.hasSubFields = function (field) {
		        var message_field = $scope.wrapper.message[field.msg_key + '_' + field.input];
		        return message_field !== undefined && message_field !== null && message_field.sub_fields !== undefined;
	        };
	        
	        /**
		     * Returns a given field's sub fields.
		     * @param {Object} field - the field we are interested in.
		     * @returns {Object|Array} - the fields sub fields, may be Object or Array.
		     */
	        $scope.getSubFields = function (field) {
		        return $scope.wrapper.message[field.msg_key + '_' + field.input].sub_fields;
	        };
            
        }
    };
}

angular.module('promenade.endpoints.standardendpoint.commands', ['RecursionHelper', 'parlay.store', 'parlay.navigation.bottombar', 'parlay.utility'])
	.controller('PromenadeStandardEndpointCardCommandTabController', ['$scope', '$timeout', 'ScriptLogger', 'ParlayUtility', PromenadeStandardEndpointCardCommandTabController])
	.directive("promenadeStandardEndpointCardCommands", PromenadeStandardEndpointCardCommands)
	.directive("promenadeStandardEndpointCardCommandContainer", ['RecursionHelper', 'ParlayPersistence', 'ParlayUtility', PromenadeStandardEndpointCardCommandContainer]);