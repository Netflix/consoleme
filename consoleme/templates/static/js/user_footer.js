$(document).ready(function () {
  $("#groups").DataTable({
    order: [[1, "asc"]],
    displayLength: 25,
  });
});

$(".message .close").on("click", function () {
  $(this).closest(".message").transition("fade");
});

document
  .getElementById("user_modify_form")
  .addEventListener("submit", async function (event) {
    event.preventDefault();
    document.getElementById("error_div").classList.add("hidden");
    document.getElementById("success_div").classList.add("hidden");
    let arr = $(this).serializeArray();
    let json = JSON.stringify(arr);
    $(".ui.dimmer").addClass("active");
    let res = await sendRequestCommon(json);
    $(".ui.dimmer").removeClass("active");
    let element = null;

    if (res.status === "error") {
      element = document.getElementById("error_response");
      element.textContent = res.message;
      document.getElementById("error_div").classList.remove("hidden");
    } else if (res.status === "success") {
      element = document.getElementById("success_response");
      element.textContent = res.message;
      document.getElementById("success_div").classList.remove("hidden");
    } else {
      element = document.getElementById("error_response");
      element.textContent = event.target.responseText;
      document.getElementById("error_div").classList.remove("hidden");
    }

    element = document.getElementById("modal_content");
    element.innerHTML = res.html;
    $(".ui.basic.modal").modal("show");
  });
