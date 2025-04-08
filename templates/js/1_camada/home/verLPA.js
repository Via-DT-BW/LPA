function verDetalhes(linha, dataAuditoria, turno, auditor) {
    fetch("/get_lpa_details", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            "linha": linha,
            "data_auditoria": dataAuditoria,
            "turno": turno
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log("Resposta da API:", data);
        var modalBody = document.getElementById('modalBody');
        if (!modalBody) {
            console.error('Elemento modalBody não encontrado.');
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
                                <p class="mb-1"><strong><i class="fas fa-clock mr-2"></i> Turno:</strong> ${turno}</p>
                                <p class="mb-1"><strong><i class="fas fa-user mr-2"></i> Auditor:</strong> ${auditor}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        modalBody.innerHTML = headerInfo;
        
        if (data.length === 0) {
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
        console.error('Erro ao carregar detalhes do LPA:', error);
        var modalBody = document.getElementById('modalBody');
        if (modalBody) {
            modalBody.innerHTML = `
                <div class="alert alert-danger text-center" role="alert">
                    <i class="fas fa-exclamation-triangle mr-2"></i>
                    Erro ao carregar os detalhes do LPA. Por favor, tente novamente.
                </div>
            `;
        }
    });
}

// Função auxiliar para formatar a data
function formatarData(dataString) {
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
        return dataString;
    }
}