function abrirModal(button) {
    const incidenciaId = button.getAttribute('data-id');
    fetch(`/api/incidencia/${incidenciaId}`)
        .then(response => response.json())
        .then(data => {
            document.getElementById('modal-nao-conformidade').textContent = data.nao_conformidade;
            document.getElementById('modal-acao-corretiva').textContent = data.acao_corretiva;
            document.getElementById('modal-comentario').textContent = data.comentario_resolucao || '-';
            document.getElementById('modal-id-incidencia').value = incidenciaId;
            document.getElementById('modal-username').value = '';
            document.getElementById('modal-password').value = '';
            document.getElementById('modal-erro').style.display = 'none';

            $('#modalVerificacao').modal('show');
        })
        .catch(err => {
            alert("Erro ao buscar dados da incidência.");
            console.error(err);
        });
}

function confirmarIncidencia() {
    const id = document.getElementById('modal-id-incidencia').value;
    const username = document.getElementById('modal-username').value;
    const password = document.getElementById('modal-password').value;

    fetch('/api/incidencia/confirmar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id, username, password })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            const erroDiv = document.getElementById('modal-erro');
            erroDiv.textContent = data.message;
            erroDiv.style.display = 'block';
        }
    })
    .catch(err => console.error(err));
}

function rejeitarIncidencia() {
    const id = document.getElementById('modal-id-incidencia').value;

    fetch('/api/incidencia/rejeitar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert("Erro ao rejeitar.");
        }
    })
    .catch(err => console.error(err));
}
