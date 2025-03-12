document.addEventListener("DOMContentLoaded", function () {
    let loginUrl = "";
  
    const navLinks = document.querySelectorAll(
      '.nav-link[data-bs-toggle="modal"]'
    );
  
    navLinks.forEach((link) => {
      link.addEventListener("click", function () {
        loginUrl = link.getAttribute("data-url");
  
        const modalTitle = document.getElementById("loginModalLabel");
        if (loginUrl === "/login_daily") {
          modalTitle.textContent = "Login - Daily Team Communication";
        } else if (loginUrl === "/login_settings") {
          modalTitle.textContent = "Login - Settings";
        }
      });
    });
  
    document.getElementById("loginButton").addEventListener("click", function () {
      const form = document.getElementById("loginForm");
      const formData = new FormData(form);
      console.log(form);
  
      fetch(loginUrl, {
        method: "POST",
        body: formData,
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            window.location.href =
              loginUrl === "/login_daily" ? "/daily" : "/settings";
          } else {
            alert("Erro ao fazer login: " + data.error);
          }
        })
        .catch((error) => console.error("Erro:", error));
    });
  });
  