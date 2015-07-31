var navigation = angular.module('parlay.navigation', ['ui.router', 'ngMaterial', 'ngMdIcons', 'promenade.broker', 'parlay.protocols', 'templates-main']);

/* istanbul ignore next */
navigation.controller('parlayToolbarController', ['$scope', '$state', '$mdSidenav', '$mdMedia', function ($scope, $state, $mdSidenav, $mdMedia) {
    // Allows view to access information from $state object. Using $current.self.name for display in toolbar
    $scope.$state = $state;
}]);

/* istanbul ignore next */
navigation.directive('parlayToolbar', function () {
    return {
        templateUrl: '../parlay_components/navigation/directives/parlay-toolbar.html',
        controller: 'parlayToolbarController'
    };
});