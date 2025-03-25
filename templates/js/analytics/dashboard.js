document.addEventListener('DOMContentLoaded', function() {
    carregarDados();
    inicializarGraficoLPAs();
    inicializarGraficoIncidencias();
});

// 🟢 Carregar dados para os cards
function carregarDados() {
    fetch('/api/analytics/dados')
        .then(response => response.json())
        .then(data => {
            // Preencher os dados nos cards
            document.getElementById('lpa-count').textContent = data.lpasRealizados;
            document.getElementById('compliance-rate').textContent = data.taxaConformidade + '%';
            document.getElementById('incidents-count').textContent = data.incidenciasAbertas;
            document.getElementById('resolution-time').textContent = data.tempoMedioResolucao + ' dias';
        })
        .catch(error => console.error('❌ Erro ao carregar dados:', error));
}

// 🟢 Gráfico de LPAs Realizados por Linha (Barra)
let lpaChart;
function inicializarGraficoLPAs() {
    fetch('/api/analytics/dados')
        .then(response => response.json())
        .then(data => {
            // Configurar o gráfico de LPAs por Linha usando Highcharts
            lpaChart = Highcharts.chart('lpaPorLinhaChart', {
                chart: {
                    type: 'column',
                    height: 300
                },
                title: {
                    text: null
                },
                xAxis: {
                    categories: data.lpasPorLinha.linhas,
                    crosshair: true
                },
                yAxis: {
                    min: 0,
                    title: {
                        text: 'LPAs Realizados'
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
                plotOptions: {
                    column: {
                        pointPadding: 0.2,
                        borderWidth: 0
                    }
                },
                series: [{
                    name: 'LPAs Realizados',
                    data: data.lpasPorLinha.valores,
                    color: '#4e73df'
                }],
                credits: {
                    enabled: false
                }
            });
        })
        .catch(error => console.error('❌ Erro ao carregar gráfico de LPAs:', error));
}

// 🟢 Gráfico de Incidências por Categoria (Pizza)
let incidenciaChart;
function inicializarGraficoIncidencias() {
    fetch('/api/analytics/dados')
        .then(response => response.json())
        .then(data => {
            // Configurar o gráfico de Incidências por Categoria usando Highcharts
            incidenciaChart = Highcharts.chart('incidenciasPorCategoriaChart', {
                chart: {
                    type: 'pie',
                    height: 300
                },
                title: {
                    text: null
                },
                tooltip: {
                    pointFormat: '{series.name}: <b>{point.y}</b> ({point.percentage:.1f}%)'
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
                    name: 'Incidências',
                    colorByPoint: true,
                    data: data.incidenciasPorCategoria.categorias.map((categoria, index) => ({
                        name: categoria,
                        y: data.incidenciasPorCategoria.valores[index]
                    }))
                }],
                colors: ['#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b'],
                credits: {
                    enabled: false
                }
            });
        })
        .catch(error => console.error('❌ Erro ao carregar gráfico de incidências:', error));
}

// Função para mudar o período dos gráficos
function mudarPeriodo(periodo) {
    // Atualizar os gráficos com base no período selecionado
    fetch(`/api/analytics/dados?periodo=${periodo}`)
        .then(response => response.json())
        .then(data => {
            // Atualizar os dados nos cards
            document.getElementById('lpa-count').textContent = data.lpasRealizados;
            document.getElementById('compliance-rate').textContent = data.taxaConformidade + '%';
            
            // Atualizar o gráfico de LPAs
            if (lpaChart) {
                lpaChart.update({
                    xAxis: {
                        categories: data.lpasPorLinha.linhas
                    },
                    series: [{
                        data: data.lpasPorLinha.valores
                    }]
                });
            }
            
            // Atualizar o gráfico de Incidências
            if (incidenciaChart) {
                incidenciaChart.update({
                    series: [{
                        data: data.incidenciasPorCategoria.categorias.map((categoria, index) => ({
                            name: categoria,
                            y: data.incidenciasPorCategoria.valores[index]
                        }))
                    }]
                });
            }
        })
        .catch(error => console.error('❌ Erro ao atualizar dados por período:', error));
}

// Função para exportar relatório
function exportarRelatorio() {
    // Implementar lógica de exportação usando Highcharts exporting module
    if (lpaChart && incidenciaChart) {
        // Exportar os gráficos como imagens
        lpaChart.exportChart({
            type: 'application/pdf',
            filename: 'relatorio-lpas'
        });
    } else {
        alert('Preparando relatório para exportação...');
        // Implementar lógica de exportação de relatório completo
    }
}