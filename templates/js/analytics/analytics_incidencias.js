document.addEventListener('DOMContentLoaded', function() {
    // Inicializar data dos filtros
    configurarDatas();
    
    // Carregar opções de filtros
    carregarOpcoesFiltros();
    
    // Carregar dados iniciais
    carregarDadosIncidencias();
    
    // Inicializar gráficos
    inicializarGraficos();
});

function configurarDatas() {
    // Configurar data final como hoje
    const hoje = new Date();
    const dataFim = document.getElementById('dataFim');
    dataFim.valueAsDate = hoje;
    
    // Configurar data início como há 30 dias
    const dataInicio = new Date();
    dataInicio.setDate(hoje.getDate() - 30);
    document.getElementById('dataInicio').valueAsDate = dataInicio;
}

function carregarOpcoesFiltros() {
    // Carregar opções de linhas
    fetch('/api/linhas')
        .then(response => response.json())
        .then(data => {
            const linhaSelect = document.getElementById('linha');
            data.forEach(linha => {
                const option = document.createElement('option');
                option.value = linha.id;
                option.textContent = linha.nome;
                linhaSelect.appendChild(option);
            });
        })
        .catch(error => console.error('Erro ao carregar linhas:', error));
    
    // Carregar opções de categorias
    fetch('/api/categorias-incidencias')
        .then(response => response.json())
        .then(data => {
            const categoriaSelect = document.getElementById('categoria');
            data.forEach(categoria => {
                const option = document.createElement('option');
                option.value = categoria.id;
                option.textContent = categoria.nome;
                categoriaSelect.appendChild(option);
            });
        })
        .catch(error => console.error('Erro ao carregar categorias:', error));
}

function aplicarFiltros() {
    // Obter valores dos filtros
    const dataInicio = document.getElementById('dataInicio').value;
    const dataFim = document.getElementById('dataFim').value;
    const linha = document.getElementById('linha').value;
    const categoria = document.getElementById('categoria').value;
    
    // Recarregar dados com filtros
    carregarDadosIncidencias(dataInicio, dataFim, linha, categoria);
    
    // Notificar usuário
    toastr.success("Filtros aplicados com sucesso!", "Sucesso");
}

function carregarDadosIncidencias(dataInicio, dataFim, linha, categoria) {
    // Construir URL com parâmetros de filtro
    let url = '/api/analytics/incidencias';
    const params = new URLSearchParams();
    
    if (dataInicio) params.append('data_inicio', dataInicio);
    if (dataFim) params.append('data_fim', dataFim);
    if (linha) params.append('linha_id', linha);
    if (categoria) params.append('categoria_id', categoria);
    
    if (params.toString()) {
        url += '?' + params.toString();
    }
    
    // Carregar dados da tabela
    fetch(url)
        .then(response => response.json())
        .then(data => {
            const tbody = document.querySelector('#incidenciasTable tbody');
            tbody.innerHTML = '';
            
            data.forEach(item => {
                const tr = document.createElement('tr');
                
                // Determinar classe de estado
                let estadoClass;
                switch (item.estado) {
                    case 'Aberta':
                        estadoClass = 'badge-warning';
                        break;
                    case 'Em Resolução':
                        estadoClass = 'badge-info';
                        break;
                    case 'Resolvida':
                        estadoClass = 'badge-success';
                        break;
                    default:
                        estadoClass = 'badge-secondary';
                }
                
                tr.innerHTML = `
                    <td>${item.id}</td>
                    <td>${formatarData(item.data)}</td>
                    <td>${item.linha}</td>
                    <td>${item.categoria}</td>
                    <td>${item.descricao}</td>
                    <td><span class="badge ${estadoClass}">${item.estado}</span></td>
                    <td>
                        <button class="btn btn-info btn-sm" onclick="verDetalhes(${item.id})">
                            <i class="fas fa-eye"></i>
                        </button>
                    </td>
                `;
                
                tbody.appendChild(tr);
            });
            
            // Atualizar gráficos com novos dados
            atualizarGraficos(data);
        })
        .catch(error => console.error('Erro ao carregar incidências:', error));
}

function inicializarGraficos() {
    // Inicializar gráfico de tendência
    const tendenciaOptions = {
        series: [{
            name: 'Incidências',
            data: []
        }],
        chart: {
            height: 300,
            type: 'line',
            toolbar: {
                show: false
            }
        },
        xaxis: {
            categories: [],
            labels: {
                rotate: -45,
                style: {
                    fontSize: '12px'
                }
            }
        },
        colors: ['#e74a3b']
    };
    
    window.tendenciaChart = new ApexCharts(document.querySelector("#tendenciaIncidenciasChart"), tendenciaOptions);
    window.tendenciaChart.render();
    
    // Inicializar gráfico de incidências por linha
    const linhasOptions = {
        series: [],
        chart: {
            height: 300,
            type: 'bar',
            toolbar: {
                show: false
            }
        },
        plotOptions: {
            bar: {
                horizontal: true
            }
        },
        dataLabels: {
            enabled: false
        },
        xaxis: {
            categories: []
        },
        colors: ['#4e73df']
    };
    
    window.linhasChart = new ApexCharts(document.querySelector("#incidenciasPorLinhaChart"), linhasOptions);
    window.linhasChart.render();
}

function atualizarGraficos(dados) {
    // Processar dados para gráfico de tendência
    const dadosPorData = processarDadosPorData(dados);
    window.tendenciaChart.updateOptions({
        xaxis: {
            categories: dadosPorData.categorias
        }
    });
    window.tendenciaChart.updateSeries([{
        name: 'Incidências',
        data: dadosPorData.valores
    }]);
    
    // Processar dados para gráfico de incidências por linha
    const dadosPorLinha = processarDadosPorLinha(dados);
    window.linhasChart.updateOptions({
        xaxis: {
            categories: dadosPorLinha.categorias
        }
    });
    window.linhasChart.updateSeries([{
        name: 'Incidências',
        data: dadosPorLinha.valores
    }]);
}

function processarDadosPorData(dados) {
    // Agrupa incidências por data
    const dataMap = {};
    dados.forEach(item => {
        const data = item.data.split(' ')[0]; // Apenas a parte da data
        if (dataMap[data]) {
            dataMap[data]++;
        } else {
            dataMap[data] = 1;
        }
    });
    
    // Ordenar por data
    const datas = Object.keys(dataMap).sort();
    const valores = datas.map(data => dataMap[data]);
    
    return {
        categorias: datas,
        valores: valores
    };
}

function processarDadosPorLinha(dados) {
    // Agrupa incidências por linha
    const linhaMap = {};
    dados.forEach(item => {
        if (linhaMap[item.linha]) {
            linhaMap[item.linha]++;
        } else {
            linhaMap[item.linha] = 1;
        }
    });
    
    // Converter para arrays
    const linhas = Object.keys(linhaMap);
    const valores = linhas.map(linha => linhaMap[linha]);
    
    return {
        categorias: linhas,
        valores: valores
    };
}

function verDetalhes(id) {
    // Lógica para exibir detalhes de uma incidência específica
    alert(`Visualizar detalhes da incidência ${id}`);
}

function formatarData(dataString) {
    // Formatar data para exibição
    const data = new Date(dataString);
    return data.toLocaleDateString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
}

function exportarRelatorio() {
    // Lógica para exportar o relatório (PDF, Excel, etc.)
    alert('Funcionalidade de exportação será implementada em breve!');
}