function verDetalhes3(linha, dataAuditoria, auditor) {
    fetch("/get_lpa_details3", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            "linha": linha,
            "data_auditoria": dataAuditoria
        })
    })
    .then(response => response.json())
    .then(data => {

        var modalBody = document.getElementById('modalBody3');
        if (!modalBody) {
            console.error('Elemento modalBody3 não encontrado.');
            return;
        }
        modalBody.innerHTML = '';

        let headerInfo = `
            <div class="audit-info-header mb-4">
                <div class="card border-primary">
                    <div class="card-body p-3">
                        <div class="row">
                            <div class="col-md-6">
                                <p class="mb-1"><strong><i class="fas fa-industry mr-2"></i> Linha:</strong> ${linha}</p>
                                <p class="mb-1"><strong><i class="fas fa-calendar-alt mr-2"></i> Data:</strong> ${formatarData(dataAuditoria)}</p>
                            </div>
                            <div class="col-md-6">
                                <p class="mb-1"><strong><i class="fas fa-user mr-2"></i> Auditor:</strong> ${auditor}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        modalBody.innerHTML = headerInfo;

        // Verificar se a resposta é um array
        if (!Array.isArray(data) || data.length === 0) {
            modalBody.innerHTML += '<p class="text-muted text-center">Nenhum detalhe encontrado.</p>';
        } else {
            let tableContent = `
                <table class="table table-striped table-hover">
                    <thead>
                        <tr>
                            <th>Pergunta</th>
                            <th class="text-center">Resposta</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            // Se a resposta for um array, processamos os dados
            data.forEach(item => {
                let responseClass = item.resposta === 'OK' ? 'status-ok' : 'status-nok';

                tableContent += `
                    <tr>
                        <td>${item.pergunta}</td>
                        <td class="text-center">
                            <span class="${responseClass}">${item.resposta}</span>
                        </td>
                    </tr>
                `;
            });

            tableContent += `</tbody></table>`;
            modalBody.innerHTML += tableContent;
        }
    })
    .catch(error => {
        console.error('Erro ao carregar detalhes do LPA 3ª Camada:', error);
        var modalBody = document.getElementById('modalBody3');
        if (modalBody) {
            modalBody.innerHTML = `
                <div class="alert alert-danger text-center" role="alert">
                    <i class="fas fa-exclamation-triangle mr-2"></i>
                    Erro ao carregar os detalhes do LPA 3ª Camada. Por favor, tente novamente.
                </div>
            `;
        }
    });
}

// Função auxiliar para formatar a data
function formatarData(dataString) {
    if (!dataString) return '-';
    try {
        const data = new Date(dataString);
        return data.toLocaleString('pt-PT', { 
            day: '2-digit', 
            month: '2-digit', 
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (e) {
        console.error("Erro ao formatar data:", e);
        return dataString;
    }
}
