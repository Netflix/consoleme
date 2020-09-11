$(document).ready(function () {
  // Search on each header
  $("#groups thead th").each(function () {
    var title = $("#groups thead th").eq($(this).index()).text();
    if (title == "Access") {
      $(this).html(
        '<select id="request_select"><option value="all">All</option><option value="requestable">Requestable groups</option><option value="member">Groups I\'m a memeber of</option><option value="not_member">Groups I\'m not a member of</option></select>'
      );
    } else {
      $(this).html('<input type="text" placeholder="Search ' + title + '" />');
    }
  });

  var table = $("#groups").DataTable({
    order: [[1, "asc"]],
    dom: "Bfrtip",
    buttons: ["csvHtml5"],
    initComplete: function () {
      $("#hide").css("display", "block");
      $("#loading").css("display", "none");
    },
    lengthMenu: [
      [10, 25, 50, 100, 1000],
      [10, 25, 50, 100, 1000],
    ],
    order: [],
    displayLength: 25,
    processing: true,
    serverSide: true,
    ajax: "get_groups",
    search: {
      regex: true,
    },
    columns: [
      {
        orderable: false,
        render: function (data, type, row, meta) {
          if (type === "display") {
            data =
              '<a target="_blank" href="/accessui/group/' +
              data +
              '">' +
              data +
              "</a>";
          }

          return data;
        },
      },
      { orderable: false },
      { orderable: false },
    ],
    sDom: '<"top"i>rt<"bottom"lpB><"clear">',
  });

  let input_filter_timeout;
  // Apply the search
  table
    .columns()
    .eq(0)
    .each(function (colIdx) {
      $("input", table.column(colIdx).header()).on("keydown", function (ev) {
        that = this;
        clearTimeout(input_filter_timeout);
        input_filter_timeout = setTimeout(function () {
          table.column(colIdx).search(that.value).draw();
        }, 350);
      });
    });

  // Allow searching on the dropdown
  table
    .columns()
    .eq(0)
    .each(function (colIdx) {
      $("select", table.column(colIdx).header()).on(
        "keyup change",
        function () {
          table.column(colIdx).search(this.value).draw();
        }
      );
    });
  let search_params = window.location.search;
  if (search_params.includes("requestable")) {
    table.column(2).search("requestable").draw();

    $(function () {
      $("#request_select").val("requestable");
    });
  }
});
