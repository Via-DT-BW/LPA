function verDetalhes(linha, dataAuditoria, turno) {
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

        if (data.error) {
            modalBody.innerHTML = `<p class="text-muted text-center">${data.error}</p>`;
        } else if (data.length === 0) {
            modalBody.innerHTML = '<p class="text-muted text-center">Nenhum detalhe encontrado.</p>';
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

            if (Array.isArray(data)) {
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
            } else {
                modalBody.innerHTML = '<p class="text-muted text-center">Formato de resposta inválido.</p>';
            }

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

function verIncidencia(incidencias, acoesCorretivas, prazo) {
    var incidenciaModalBody = document.getElementById('incidenciaModalBody');
    if (!incidenciaModalBody) {
        console.error('Elemento incidenciaModalBody não encontrado.');
        return;
    }
    incidenciaModalBody.innerHTML = `
        <p><strong>Incidências:</strong> ${incidencias}</p>
        <p><strong>Ações Corretivas:</strong> ${acoesCorretivas}</p>
        <p><strong>Prazo:</strong> ${prazo}</p>
    `;
    $('#incidenciaModal').modal('show');
}