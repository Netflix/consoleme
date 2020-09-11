$(document).ready(function () {
  // Search on each header
  $("#audit thead th").each(function () {
    let title = $("#audit thead th").eq($(this).index()).text();
    if (title == "Updated At") {
      $(this).html(
        '<input class="date_range_filter date" type="text" id="datepicker_from" placeholder="From Date (01/01/2019)"/>' +
          '<input class="date_range_filter date" type="text" id="datepicker_to" placeholder="To Date (12/31/2019)"/>'
      );
    } else {
      $(this).html('<input type="text" placeholder="Search ' + title + '" />');
    }
  });

  let table = $("#audit").DataTable({
    order: [],
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
    displayLength: 25,
    processing: true,
    serverSide: true,
    ajax: {
      url: "get_audit_logs",
      data: function (d) {
        return $.extend({}, d, {
          datepicker_from: $("#datepicker_from").val(),
          datepicker_to: $("#datepicker_to").val(),
        });
      },
    },
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
      {
        orderable: false,
        render: function (data, type, row, meta) {
          if (type === "display") {
            data =
              '<a target="_blank" href="/accessui/user/' +
              data +
              '">' +
              data +
              "</a>";
          }

          return data;
        },
      },
      {
        orderable: false,
        render: function (data, type, row, meta) {
          if (type === "display") {
            data =
              '<a target="_blank" href="/accessui/user/' +
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
      $("input", table.column(colIdx).header()).on(
        "keyup search input paste cut keydown",
        function (ev) {
          that = this;
          clearTimeout(input_filter_timeout);
          input_filter_timeout = setTimeout(function () {
            table.column(colIdx).search(that.value).draw();
          }, 350);
        }
      );
    });

  // Allow searching on the dropdown
  table
    .columns()
    .eq(0)
    .each(function (colIdx) {
      $("select", table.column(colIdx).header()).on(
        "keyup change",
        function () {
          clearTimeOut();
          table.column(colIdx).search(this.value).draw();
        }
      );
    });
});
