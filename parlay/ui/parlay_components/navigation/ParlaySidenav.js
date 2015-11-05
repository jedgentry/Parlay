function ParlaySidenav() {
	return {
		scope: {},
		templateUrl: "../parlay_components/navigation/directives/parlay-sidenav.html",
		controller: "ParlaySidenavController",
		controllerAs: "ctrl"
	};
}

function ParlaySidenavController($mdSidenav, $state) {
	
	this.closeSidenav = function() {
		$mdSidenav("navigation").close();
	};
	
	this.navigateToState = function(state_name) {
		$state.go(state_name);	
	};
	
	this.states = $state.get().filter(function(state) {
		return !state.abstract;
	}).map(function(state) {
		return {
			name: state.name,
			display: state.data.display,
			icon: state.data.icon
		};
	});
	
}

function TitlecaseFilter() {
	// http://ng.malsup.com/#!/titlecase-filter
	return function(str) {
		s = ( s === undefined || s === null ) ? '' : s;
        return s.toString().toLowerCase().replace( /\b([a-z])/g, function(ch) {
            return ch.toUpperCase();
        });
	};
}

angular.module("parlay.sidenav", ["ngMaterial", "ui.router"])
	.controller("ParlaySidenavController", ["$mdSidenav", "$state", ParlaySidenavController])
	.directive("parlaySidenav", [ParlaySidenav])
	.filter("titlecase", TitlecaseFilter);