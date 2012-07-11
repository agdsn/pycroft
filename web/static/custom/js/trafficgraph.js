function load_trafficchart(){
    var trafficchart = new Highcharts.Chart({
        chart:{
            renderTo:'trafficchart',
            type:'column',
            width:600,
            height:250,
            animation:false
        },
        title:{
            text:null
        },
        plotOptions:{
            series:{ animation:false },
            column:{ stacking:'normal' }
        },
        legend:{
            enabled:false
        },
        tooltip:{
            enabled:true,
            formatter:function () {
                var tooltip = '<b>' + this.x + '</b>';
                $.each(this.points, function (i, point) {
                    tooltip += '<br />' + point.series.name + ': ' + point.y + 'Mb';
                });
                return tooltip;
            },
            shared:true
        },
        xAxis:{
            categories:['Montag', 'Dienstag', 'Mittwoch',
                'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
        },
        yAxis:{
            title:{ text:null }
        },
        series: []
    });

    $.getJSON($("#trafficchart").data("trafficurl"), null, function(response) {
        $(response.series).each(function(idx, data) {
            trafficchart.addSeries(data);
        });
    });
}

