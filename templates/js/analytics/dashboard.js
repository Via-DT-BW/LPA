document.addEventListener('DOMContentLoaded', function() {
    carregarDados();
});

// Carregar dados para os cards e gráficos
function carregarDados() {
    fetch('/api/analytics/dados')
        .then(response => response.json())
        .then(data => {
            // Preencher os dados nos cards
            document.getElementById('total-lpa-count').textContent = data.totalLPAs;
            document.getElementById('ok-count').textContent = data.okCount;
            document.getElementById('nok-count').textContent = data.nokCount;
            document.getElementById('incidents-count').textContent = data.incidenciasAbertas;

            // Inicializar gráficos
            inicializarGraficoComparacaoLPAs(data.categorias, data.valores);
            inicializarGraficoPizza(data.okCount, data.nokCount);
        })
        .catch(error => console.error('❌ Erro ao carregar dados:', error));
}

// Gráfico de Comparação de LPAs
function inicializarGraficoComparacaoLPAs(categorias, valores) {
    Highcharts.chart('lpaComparisonChart', {
        chart: {
            type: 'column'
        },
        title: {
            text: 'Comparação de LPAs'
        },
        xAxis: {
            categories: categorias,
            title: {
                text: null
            }
        },
        yAxis: {
            min: 0,
            title: {
                text: 'Quantidade'
            }
        },
        tooltip: {
            headerFormat: '<span style="font-size:10px">{point.key}</span><table>',
            pointFormat: '<tr><td style="color:{series.color};padding:0">{series.name}: </td>' +
                '<td style="padding:0"><b>{point.y}</b></td></tr>',
            footerFormat: '</table>',
            shared: true,
            useHTML: true
        },
        series: [{
            name: 'LPAs',
            data: valores,
            color: '#4e73df'
        }],
        credits: {
            enabled: false
        }
    });
}

// Gráfico de Pizza - Percentual de Respostas OK vs NOK
function inicializarGraficoPizza(okCount, nokCount) {
    Highcharts.chart('lpaPieChart', {
        chart: {
            type: 'pie'
        },
        title: {
            text: 'Distribuição de Respostas OK/NOK'
        },
        tooltip: {
            pointFormat: '{series.name}: <b>{point.percentage:.1f}%</b>'
        },
        accessibility: {
            point: {
                valueSuffix: '%'
            }
        },
        plotOptions: {
            pie: {
                allowPointSelect: true,
                cursor: 'pointer',
                dataLabels: {
                    enabled: true,
                    format: '<b>{point.name}</b>: {point.percentage:.1f} %'
                }
            }
        },
        series: [{
            name: 'Respostas',
            colorByPoint: true,
            data: [{
                name: 'OK',
                y: okCount,
                color: '#28a745' // Verde
            }, {
                name: 'NOK',
                y: nokCount,
                color: '#dc3545' // Vermelho
            }]
        }],
        credits: {
            enabled: false
        }
    });
}
