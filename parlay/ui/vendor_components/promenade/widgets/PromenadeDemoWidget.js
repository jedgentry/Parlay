function PromenadeDemoWidget(ParlayWidgetInputManager) {
    return {
        restrict: "E",
        templateUrl: "../vendor_components/promenade/widgets/directives/promenade-demo-widget.html",
        require: "^parlayBaseWidget",
        link: function (scope, element) {

            ParlayWidgetInputManager.registerInputs(element, scope);

            this.smoothie = new SmoothieChart({
                grid: {
                    strokeStyle:'rgb(125, 0, 0)',
                    fillStyle:'rgb(60, 0, 0)',
                    lineWidth: 1,
                    millisPerLine: 250,
                    verticalSections: 6
                },
                labels: {
                    fillStyle:'rgb(60, 0, 0)'
                }
            });

            this.smoothie.streamTo(element.find("canvas")[0], 1000);

            var line = new TimeSeries();
            this.smoothie.addTimeSeries(line);

            scope.$watch("transformedValue", function (newValue) {
                if (!!newValue) {
                    line.append(new Date().getTime(), newValue);
                }
            });

        }
    };
}

angular.module("promenade.widgets.demo", ["parlay.widgets.base"])
    .directive("promenadeDemoWidget", ["ParlayWidgetInputManager", PromenadeDemoWidget]);
