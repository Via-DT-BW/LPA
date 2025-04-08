document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const lineFilterForm = document.querySelector('form[method="GET"]');
    const lineSelect = document.getElementById('linha');
    const tableRows = document.querySelectorAll('table tbody tr');

    // Line Filter Handling
    function setupLineFilter() {
        if (!lineFilterForm || !lineSelect) return;

        lineFilterForm.addEventListener('submit', function(e) {
            // Optional: Add client-side validation
            const selectedLine = lineSelect.value;
            
            // Update URL with selected line filter
            const currentUrl = new URL(window.location.href);
            if (selectedLine) {
                currentUrl.searchParams.set('linha', selectedLine);
            } else {
                currentUrl.searchParams.delete('linha');
            }
            window.location.href = currentUrl.toString();
            
            e.preventDefault();
        });

        // Highlight selected line in dropdown
        const urlParams = new URLSearchParams(window.location.search);
        const currentLinhaFilter = urlParams.get('linha');
        if (currentLinhaFilter) {
            lineSelect.value = currentLinhaFilter;
        }
    }

    // Table Row Interaction
    function enhanceTableInteraction() {
        tableRows.forEach(row => {
            // Add hover effect
            row.addEventListener('mouseenter', function() {
                this.classList.add('table-hover');
            });

            row.addEventListener('mouseleave', function() {
                this.classList.remove('table-hover');
            });

            // Optional: Add click handler for row actions
            row.addEventListener('click', function() {
                const actionButton = this.querySelector('.btn-primary');
                if (actionButton) {
                    actionButton.click();
                }
            });
        });
    }

    // Pagination Handling (if needed)
    function setupPagination() {
        const paginationLinks = document.querySelectorAll('.pagination a');
        paginationLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const pageUrl = new URL(this.href);
                window.location.href = pageUrl.toString();
            });
        });
    }

    // Toastr Notification Configuration
    function configureToastr() {
        if (typeof toastr !== 'undefined') {
            toastr.options = {
                "closeButton": true,
                "debug": false,
                "newestOnTop": false,
                "progressBar": true,
                "positionClass": "toast-top-right",
                "preventDuplicates": false,
                "onclick": null,
                "showDuration": "300",
                "hideDuration": "1000",
                "timeOut": "5000",
                "extendedTimeOut": "1000",
                "showEasing": "swing",
                "hideEasing": "linear",
                "showMethod": "fadeIn",
                "hideMethod": "fadeOut"
            };

            // Show success message if line filter applied
            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.get('linha')) {
                toastr.success('Filtro de linha aplicado com sucesso!', 'Filtro');
            }
        }
    }

    // Error Handling
    function setupErrorHandling() {
        window.addEventListener('error', function(event) {
            console.error('Erro de script:', event.error);
            if (typeof toastr !== 'undefined') {
                toastr.error('Ocorreu um erro inesperado', 'Erro');
            }
        });
    }

    // Initialize all functions
    function init() {
        setupLineFilter();
        enhanceTableInteraction();
        setupPagination();
        configureToastr();
        setupErrorHandling();
    }

    // Run initialization
    init();
});

