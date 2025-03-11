   
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

            if (data.length === 0) {
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

    document.getElementById('apply-filters').addEventListener('click', function() {
        var linha = document.getElementById('linha').value;
        var turno = document.getElementById('turno').value;

        toastr.success('Filtro aplicado com sucesso!', 'Sucesso');
    });
}

