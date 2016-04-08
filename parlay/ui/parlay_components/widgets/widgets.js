/**
 * @name WidgetsConfiguration
 * @param $stateProvider - Service provided by ui.router
 * @description - The WidgetsConfiguration sets up the items state.
 */
function WidgetsConfiguration($stateProvider) {
    $stateProvider.state("widgets", {
        url: "/widgets",
        templateUrl: "../parlay_components/widgets/views/base.html",
        controller: "ParlayWidgetsController",
        controllerAs: "widgetsCtrl",
        data: {
            displayName: "Widgets",
            displayIcon: "create"
        }
    });
}

function ParlayWidgetsController() {
    
    this.items = [];

    this.add = function () {
        this.items.push({});
    };

    this.remove = function (index) {
        this.items.splice(index, 1);
    };
    
}

angular.module("parlay.widgets", ["ui.router", "ui.ace", "ngMaterial", "parlay.widgets.base", "promenade.widgets.display", "promenade.widgets.input", "promenade.widgets.graph", "promenade.widgets.button"])
    .config(WidgetsConfiguration)
    .controller("ParlayWidgetsController", [ParlayWidgetsController]);