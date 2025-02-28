function formatarDataAtual() {
    const dataAtual = new Date();
    const dia = String(dataAtual.getDate()).padStart(2, '0');
    const mes = String(dataAtual.getMonth() + 1).padStart(2, '0');
    const ano = dataAtual.getFullYear();
    const horas = String(dataAtual.getHours()).padStart(2, '0');
    const minutos = String(dataAtual.getMinutes()).padStart(2, '0');
    
    return `${dia}/${mes}/${ano} - ${horas}:${minutos}`;
}

function formatarDataPrazo(data) {
    var date = new Date(data); 
    var ano = date.getFullYear();
    var mes = String(date.getMonth() + 1).padStart(2, '0');
    var dia = String(date.getDate()).padStart(2, '0');
    
    return `${ano}-${mes}-${dia}`;
}
