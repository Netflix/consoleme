async function accessuiApproveRejectFlow(clicked_id, reviewer_comments) {
  document.getElementById("error_div").classList.add("hidden");
  document.getElementById("success_div").classList.add("hidden");
  let arr = [
    { name: "updated_status", value: clicked_id },
    { name: "reviewer_comments", value: reviewer_comments },
  ];
  let json = JSON.stringify(arr);
  $(".ui.dimmer").addClass("active");
  await sendRequestCommon(json);
  location.reload();
}
