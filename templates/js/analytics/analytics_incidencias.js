document.addEventListener('DOMContentLoaded', function() {
    carregarDadosIncidencias();
    inicializarGraficos();
});

function carregarDadosIncidencias() {
    fetch('/api/analytics/incidencias')
        .then(response => response.json())
        .then(data => {
            console.log('Resposta da API:', data);

            if (!data.incidencias || data.incidencias.length === 0) {
                console.warn("Nenhuma incidência encontrada.");
                document.querySelector('#incidenciasTable tbody').innerHTML = '';
                document.getElementById('totalIncidencias').textContent = '0';
                document.getElementById('incidenciasPendentes').textContent = '0';
                document.getElementById('incidenciasResolvidas').textContent = '0';
                window.linhaChart.updateSeries([]);
                window.tendenciaChart.updateSeries([]);
                return;
            }

            atualizarTabelaIncidencias(data.incidencias);
            atualizarEstatisticas(data);
            atualizarGraficos(data);
        })
        .catch(error => {
            console.error('Erro ao carregar incidências:', error);
            toastr.error('Erro ao carregar dados de incidências.', 'Erro');
        });
}

function atualizarTabelaIncidencias(incidencias) {
    const tbody = document.querySelector('#incidenciasTable tbody');
    tbody.innerHTML = '';

    incidencias.forEach(incidencia => {
        const tr = document.createElement('tr');

        const resolvido = incidencia.resolvido === 'True';
        const estadoClass = resolvido ? 'badge-success' : 'badge-danger';
        const estadoTexto = resolvido ? 'Resolvida' : 'Pendente';

        tr.innerHTML = `
            <td>${incidencia.id}</td>
            <td>${formatarData(incidencia.data_auditoria)}</td>
            <td>${incidencia.linha || 'Não especificada'}</td>
            <td>${incidencia.turno || 'Não especificado'}</td>
            <td>${incidencia.nao_conformidade || 'Não especificada'}</td>
            <td>${incidencia.acao_corretiva || 'Não definida'}</td>
            <td>${formatarData(incidencia.prazo)}</td>
            <td>
                <span class="badge ${estadoClass}">${estadoTexto}</span>
            </td>
            <td>
                <button class="btn btn-info btn-sm" onclick="verDetalhesIncidencia(${incidencia.id})">
                    <i class="fas fa-eye"></i>
                </button>
            </td>
        `;

        tbody.appendChild(tr);
    });
}


function atualizarEstatisticas(data) {
    document.getElementById('totalIncidencias').textContent = data.total_incidencias || 0;
    document.getElementById('incidenciasPendentes').textContent = data.incidencias_pendentes || 0;
    document.getElementById('incidenciasResolvidas').textContent = data.incidencias_resolvidas || 0;
}

function inicializarGraficos() {
    window.linhaChart = Highcharts.chart("incidenciasPorSetorChart", {
        chart: { type: 'column', backgroundColor: '#f4f4f9' },
        title: { text: 'Incidências por Setor' },
        xAxis: { categories: [], title: { text: 'Setor' } },
        yAxis: { title: { text: 'Número de Incidências' } },
        series: [{ name: 'Incidências', data: [0], color: '#007bff' }]
    });

    window.tendenciaChart = Highcharts.chart("tendenciaIncidenciasChart", {
        chart: { type: 'line', backgroundColor: '#f4f4f9', zoomType: 'xy' },
        title: { text: 'Tendência de Incidências' },
        xAxis: { categories: [], title: { text: 'Data' } },
        yAxis: { title: { text: 'Número de Incidências' } },
        series: [{ name: 'Incidências', data: [], color: '#007bff' }]
    });
}

function atualizarGraficos(data) {
    // Check if incidencias_por_linha_tempo data exists and has data
    if (!data.incidencias_por_linha_tempo || 
        !data.incidencias_por_linha_tempo.linhas || 
        data.incidencias_por_linha_tempo.linhas.length === 0) {
        
        // Reset both charts if no data
        window.linhaChart.update({
            xAxis: { categories: [] },
            series: [{ name: 'Incidências', data: [] }]
        });

        window.tendenciaChart.update({
            xAxis: { categories: [] },
            series: []
        });

        return;
    }

    // Preparar dados para o gráfico de Incidências por Setor
    const dadosSetores = data.incidencias_por_linha_tempo.linhas.map((linha, index) => ({
        name: linha,
        y: data.incidencias_por_linha_tempo.series[index].reduce((a, b) => a + b, 0)
    }));

    // Atualizar gráfico de Incidências por Setor
    window.linhaChart.update({
        xAxis: { 
            categories: data.incidencias_por_linha_tempo.linhas 
        },
        series: [{ 
            name: 'Incidências', 
            data: dadosSetores.map(dado => dado.y),
            color: '#007bff'
        }]
    });

    // Preparar dados para o gráfico de Tendência de Incidências
    const seriesData = data.incidencias_por_linha_tempo.linhas.map((linha, index) => ({
        name: linha,
        data: data.incidencias_por_linha_tempo.series[index],
        color: Highcharts.getOptions().colors[index % Highcharts.getOptions().colors.length],
    }));

    // Atualizar gráfico de Tendência de Incidências
    window.tendenciaChart.update({
        xAxis: {
            categories: data.incidencias_por_linha_tempo.datas,
            title: { text: 'Data' }
        },
        yAxis: {
            title: { text: 'Número de Incidências' }
        },
        series: seriesData
    });
}


function verDetalhesIncidencia(id) {
    fetch(`/api/incidencia/${id}`)
        .then(response => response.json())
        .then(incidencia => {
            const modal = new bootstrap.Modal(document.getElementById('detalhesIncidenciaModal'));

            document.getElementById('modalNaoConformidade').textContent = incidencia.nao_conformidade || 'Não especificada';
            document.getElementById('modalAcaoCorretiva').textContent = incidencia.acao_corretiva || 'Não definida';
            document.getElementById('modalPrazo').textContent = formatarData(incidencia.prazo);
            document.getElementById('modalResolvido').textContent = incidencia.resolvido === 'True' ? 'Sim' : 'Não';
            document.getElementById('modalComentarioResolucao').textContent = incidencia.comentario_resolucao || 'Nenhum';
            
            modal.show();
        })
        .catch(error => {
            console.error('Erro ao carregar detalhes da incidência:', error);
            toastr.error('Erro ao carregar detalhes da incidência.', 'Erro');
        });
}

function formatarData(dataString) {
    if (!dataString) return 'Não definida';
    const data = new Date(dataString);
    return data.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
}
