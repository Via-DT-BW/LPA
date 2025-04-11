function abrirModal(btn) {
    const id = $(btn).data('id');
    
    // Buscar informações da incidência para preencher o modal
    $.ajax({
        url: '/get_incidencia_info',
        type: 'GET',
        data: { id: id },
        success: function(response) {
            $('#modal-nao-conformidade').text(response.nao_conformidade);
            $('#modal-acao-corretiva').text(response.acao_corretiva);
            $('#modal-comentario').text(response.comentario_resolucao);
            $('#modal-id-incidencia').val(id);
            
            // Reset dos campos
            $('#modal-username').val('');
            $('#modal-password').val('');
            $('#modal-erro').hide();
            
            $('#modalVerificacao').modal('show');
        },
        error: function() {
            toastr.error('Erro ao carregar informações da incidência');
        }
    });
}

function confirmarIncidencia() {
    const id = $('#modal-id-incidencia').val();
    const username = $('#modal-username').val();
    const password = $('#modal-password').val();
    
    if (!username || !password) {
        $('#modal-erro').text('Por favor, preencha o username e password').show();
        return;
    }
    
    // Botão com loading
    const $btn = $('.modal-footer .btn-success');
    const originalText = $btn.html();
    $btn.html('<i class="fas fa-spinner fa-spin mr-2"></i> Processando...').prop('disabled', true);
    
    $.ajax({
        url: '/finalizar_incidencia',
        type: 'POST',
        data: {
            id: id,
            username: username,
            password: password,
            action: 'confirmar'
        },
        success: function(response) {
            $('#modalVerificacao').modal('hide');
            toastr.success('Incidência verificada com sucesso!');
            setTimeout(function() {
                location.reload();
            }, 1500);
        },
        error: function(xhr) {
            let errorMsg = "Erro ao verificar a incidência";
            if (xhr.responseJSON && xhr.responseJSON.error) {
                errorMsg = xhr.responseJSON.error;
            }
            $('#modal-erro').text(errorMsg).show();
            $btn.html(originalText).prop('disabled', false);
        }
    });
}

function rejeitarIncidencia() {
    const id = $('#modal-id-incidencia').val();
    const username = $('#modal-username').val();
    const password = $('#modal-password').val();
    
    if (!username || !password) {
        $('#modal-erro').text('Por favor, preencha o username e password').show();
        return;
    }
    
    // Botão com loading
    const $btn = $('.modal-footer .btn-danger');
    const originalText = $btn.html();
    $btn.html('<i class="fas fa-spinner fa-spin mr-2"></i> Processando...').prop('disabled', true);
    
    $.ajax({
        url: '/finalizar_incidencia',
        type: 'POST',
        data: {
            id: id,
            username: username,
            password: password,
            action: 'rejeitar'
        },
        success: function(response) {
            $('#modalVerificacao').modal('hide');
            toastr.success('Incidência rejeitada com sucesso!');
            setTimeout(function() {
                location.reload();
            }, 1500);
        },
        error: function(xhr) {
            let errorMsg = "Erro ao rejeitar a incidência";
            if (xhr.responseJSON && xhr.responseJSON.error) {
                errorMsg = xhr.responseJSON.error;
            }
            $('#modal-erro').text(errorMsg).show();
            $btn.html(originalText).prop('disabled', false);
        }
    });
}