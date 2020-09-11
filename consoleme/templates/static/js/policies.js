$(document).ready(function () {
  // Search on each header
  $("#policies thead th").each(function () {
    var title = $("#policies thead th").eq($(this).index()).text();
    if (title == "Errors") {
      $(this).html(
        '<select id="request_select"><option value="">Do not sort by errors</option><option value="errors">Sort by number of CloudTrail errors</option></select>'
      );
    } else {
      $(this).html('<input type="text" placeholder="Search ' + title + '" />');
    }
  });

  var table = $("#policies").DataTable({
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
    displayLength: 25,
    processing: true,
    serverSide: true,
    ajax: {
      url: "/policies/get_policies",
      data: function (d) {
        return d;
      },
    },
    search: {
      regex: true,
    },
    columns: [
      {
        orderable: false,
        render: function (data, type, row, meta) {
          return data;
        },
      },
      { orderable: false },
      {
        orderable: false,
        render: function (data, type, row, meta) {
          if (type === "display") {
            let link = row[6];
            if (link) {
              data = '<a target="_blank" href=' + link + ">" + data + "</a>";
            }
          }
          return data;
        },
      },
      { orderable: false },
      {
        orderable: false,
        render: function (data, type, row, meta) {
          if (type === "display") {
            if (data == null) {
              data = "N/A";
            } else {
              let template_uri = data.split("/");
              data =
                '<a target="_blank" href="' +
                data +
                '">' +
                template_uri[template_uri.length - 1] +
                "</a>";
            }
          }

          return data;
        },
      },
      { orderable: false },
    ],
    createdRow: function (row, data, dataIndex) {
      if (parseInt(data[5], 10) > 0) {
        $(row).addClass("negative");
      }
    },
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
          table.column(colIdx).search(this.value).draw();
        }
      );
    });
});

$(".ui.accordion").accordion({
  exclusive: false,
});
