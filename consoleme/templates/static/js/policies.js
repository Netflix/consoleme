$(document).ready(function () {
  // Search on each header
  $('#policies thead th').each(function () {
    var title = $('#policies thead th').eq($(this).index()).text();
    if (title == "Errors") {
      $(this).html('<select id="request_select"><option value="">Do not sort by errors</option><option value="errors">Sort by number of CloudTrail errors</option></select>');
    } else {
      $(this).html('<input type="text" placeholder="Search ' + title + '" />');
    }
  });

  var table = $('#policies').DataTable({
    "order": [[1, "asc"]],
    "dom": 'Bfrtip',
    "buttons": ['csvHtml5'],
    "initComplete": function () {
      $('#hide').css('display', 'block');
      $('#loading').css('display', 'none');
    },
    "lengthMenu": [[10, 25, 50, 100, 1000], [10, 25, 50, 100, 1000]],
    "order": [],
    "displayLength": 25,
    "processing": true,
    "serverSide": true,
    "ajax": "/policies/get_policies",
    "search": {
      "regex": true
    },
    "columns": [
      {
        "orderable": false,
        "render": function (data, type, row, meta) {
          return data;
        }
      },
      {"orderable": false},
      {
        "orderable": false,
        "render": function (data, type, row, meta) {
          if (type === 'display') {
            let account_id = row[0];
            let resource_name = data.split(":")[5];
            let split_resource_name = resource_name.split("/");
            let is_service_role = (split_resource_name[1] === "aws-service-role");
            let iam_resource_name = split_resource_name.slice(1).join("/");
            let resource_type = data.split(":")[2];
            if (resource_type === "iam" && !data.split(":")[5].startsWith("role/")) {
              resource_type = "iam_other"
            }
            let region = data.split(":")[3];
            if (!is_service_role && resource_type === "iam") {
              data = '<a target="_blank" href="/policies/edit/' + account_id + '/iamrole/' + iam_resource_name + '">' + data + '</a>';
            }
            else if (resource_type === "s3") {
              data = '<a target="_blank" href="/policies/edit/' + account_id + '/s3/' + resource_name + '">' + data + '</a>';
            }
            else if (resource_type === "sqs") {
              data = '<a target="_blank" href="/policies/edit/' + account_id + '/sqs/' + region + '/' + resource_name + '">' + data + '</a>';
            }
            else if (resource_type === "sns") {
              data = '<a target="_blank" href="/policies/edit/' + account_id + '/sns/' + region + '/' + resource_name + '">' + data + '</a>';
            }
          }
          return data;
        }
      },
      {"orderable": false},
      {
        "orderable": false,
        "render": function (data, type, row, meta) {
          if (type === 'display') {
            if (data == null) {
              data = 'N/A';
            } else {
              let template_uri = data.split("/");
              data = '<a target="_blank" href="' + data + '">' + template_uri[template_uri.length -1] + '</a>';
            }
          }

          return data;
        }
      },
      {"orderable": false},
    ],
    "createdRow": function( row, data, dataIndex){
                if( parseInt(data[5], 10) > 0){
                    $(row).addClass('negative');
                }
    },
    "sDom": '<"top"i>rt<"bottom"lpB><"clear">'
  });

  let input_filter_timeout;

// Apply the search
  table.columns().eq(0).each(function (colIdx) {
    $('input', table.column(colIdx).header()).on('keyup search input paste cut keydown', function (ev) {
      that = this;
      clearTimeout(input_filter_timeout);
      input_filter_timeout = setTimeout(function () {
          table
            .column(colIdx)
            .search(that.value)
            .draw();
        },
        350);
    });
  });

// Allow searching on the dropdown
  table.columns().eq(0).each(function (colIdx) {
    $('select', table.column(colIdx).header()).on('keyup change', function () {
      table
        .column(colIdx)
        .search(this.value)
        .draw();
    });
  });
});


$('.ui.accordion')
  .accordion({
    exclusive: false
  })
;