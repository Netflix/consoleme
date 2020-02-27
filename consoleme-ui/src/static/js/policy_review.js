
async function policyApproveRejectFlow(clicked_id, request_id, reviewer_comments, policy_name, original_policy_document,
                                       editor) {
  // If request is approved, we want to ensure lint has passed.

  let updated_policy_document = editor.getValue();
  let lint_errors = differ.editors.right.ace.getSession().getAnnotations();
  if (lint_errors.length > 0) {
    Swal.fire(
      'Lint Error',
      JSON.stringify(lint_errors),
      'error'
    );
    return false;
  }
  document.getElementById('error_div').classList.add('hidden');
  document.getElementById('success_div').classList.add('hidden');
  let arr = {
    'request_id': request_id,
    'updated_status': clicked_id,
    'reviewer_comments': reviewer_comments,
    'policy_name': policy_name,
    'original_policy_document': original_policy_document,
    'updated_policy_document': updated_policy_document
  };
  let json = JSON.stringify(arr);
  $('.ui.dimmer').addClass('active');
  let res = await sendRequestCommon(json);
  await handleResponse(res);
  $('.ui.dimmer').removeClass('active');
}

function scrollToDiff(diffNum)
{
    let diffs = differ.diffs;

    if ( diffs.length <= diffNum )
    {
        return;
    }
    let lrow = diffs[diffNum].leftStartLine;
    let rrow = diffs[diffNum].rightStartLine;

    if ( lrow > 5 )
    {
        lrow -= 5;
    }

    if ( rrow > 5 )
    {
        rrow -= 5;
    }

    differ.getEditors().left.scrollToLine( lrow );
    differ.getEditors().right.scrollToLine( rrow );
}
