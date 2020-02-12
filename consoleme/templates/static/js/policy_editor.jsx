import React from 'react'
import ReactDOM from 'react-dom'
import { Provider } from 'react-redux'
import SelfServiceForm from "./SelfServiceForm";
import { store } from "./SelfServiceFunctions"

let tagInt = 0;

export let inlinePolicyCharClass = /[0-9A-Za-z_\-.]/g;

export async function AddManagedPolicy(policy_name, policy_arn, role_arn) {
  // First see if they are authorized and which flow we should put the user through
  let result = await Swal.fire({
    title: 'Are you sure?',
    text: "Are you sure you want to add " + policy_arn + " to " + role_arn + "?",
    type: 'warning',
    showCancelButton: true,
    confirmButtonColor: '#3085d6',
    cancelButtonColor: '#d33',
    confirmButtonText: 'Yes, add it.'
  });
  if (result.value) {
    let arr = [{'type': 'ManagedPolicy', 'name': policy_name, 'action': 'attach', 'arn': policy_arn}];
    let json = JSON.stringify(arr);
    let dimmer = $('.ui.dimmer');
    dimmer.addClass('active');
    let res = await sendRequestCommon(json);
    dimmer.removeClass('active');
    await handleResponse(res);
  }
}

export async function removeManagedPolicy(policy_name, policy_arn, role_arn) {
  // First see if they are authorized and which flow we should put the user through
    $(".circular.ui.icon.button").removeClass( "active" );
    let result = await Swal.fire({
    title: 'Are you sure?',
    text: "Are you sure you want to remove " + policy_arn + " from " + role_arn + "?",
    type: 'warning',
    showCancelButton: true,
    confirmButtonColor: '#3085d6',
    cancelButtonColor: '#d33',
    confirmButtonText: 'Yes, remove it.'
  });
  if (result.value) {
    let arr = [{'type': 'ManagedPolicy', 'name': policy_name, 'action': 'detach', 'arn': policy_arn}];
    let json = JSON.stringify(arr);
    let dimmer = $('.ui.dimmer');
    dimmer.addClass('active');
    let res = await sendRequestCommon(json);
    dimmer.removeClass('active');
    await handleResponse(res);
  }
}

export async function editPolicy(policy_type, policy_name, editor_value, is_new=false) {

  if(typeof policy_name == 'undefined' || policy_name === "") {
      Swal.fire(
        'Policy Error',
        'Policy name must not be empty',
        'error'
      );
      return false;
  }

  let lint_errors = editor_value.getSession().getAnnotations();
  if (lint_errors.length > 0) {
    Swal.fire(
      'Lint Error',
      JSON.stringify(lint_errors),
      'error'
    );
    return false;
  }

  let arr = [{'type': policy_type, 'name': policy_name, 'value': eval(editor_value).getValue(), 'is_new': is_new}];
  let json = JSON.stringify(arr);
  let dimmer = $('.ui.dimmer');
  dimmer.addClass('active');
  let res = await sendRequestCommon(json);
  dimmer.removeClass('active');
  await handleResponse(res);
}

export async function submitPolicyForReview(policy_type, policy_name, editor_value, arn, account_id, is_new=false) {

  if(policy_name === "") {
    Swal.fire(
        'Policy Error',
        'Policy name must not be empty',
        'error'
    );
    return false;
  }

  let lint_errors = editor_value.getSession().getAnnotations();
  if (lint_errors.length > 0) {
    Swal.fire(
      'Lint Error',
      JSON.stringify(lint_errors),
      'error'
    );
    return false;
  }

  const {value: justification} = await Swal.fire({
    title: 'Please let us know your use case for this change',
    input: 'textarea',
    showCancelButton: true,
    inputValidator: (value) => {
      if (!value) {
        return 'You need to write a justification.'
      }
    }
  });

  if (justification) {
    let arr = {
      "arn": arn,
      "account_id": account_id,
      "justification": justification,
      "data_list": [{'type': policy_type, 'name': policy_name, 'value': eval(editor_value).getValue(), 'is_new': is_new}]
    };
    let json = JSON.stringify(arr);
    let dimmer = $('.ui.dimmer');
    dimmer.addClass('active');
    let res = await sendRequestCommon(json, '/policies/submit_for_review');
    dimmer.removeClass('active');
    let redirect_uri = "/policies/request/" + res.request_id;
    await handleResponse(res, redirect_uri, "Success! Redirecting to the request.");
  }
}

export async function deleteTag(tag_name) {
  let arr = [{'type': "delete_tag", 'name': tag_name}];
  let json = JSON.stringify(arr);
  let dimmer = $('.ui.dimmer');
  dimmer.addClass('active');
  let res = await sendRequestCommon(json);
  dimmer.removeClass('active');
  await handleResponse(res);
}

export async function deletePolicy(policy_type, policy_name) {
  let r = confirm("Are you sure you want to delete " + policy_name + " from this role?");
  if (r !== true) {
    return false;
  }
  let arr = [{'type': policy_type, 'name': policy_name, 'action': 'detach'}];
  let json = JSON.stringify(arr);
  let dimmer = $('.ui.dimmer');
  dimmer.addClass('active');
  let res = await sendRequestCommon(json);
  dimmer.removeClass('active');
  await handleResponse(res);
}

export async function setTags() {
  let tagForm = $('#tagForm');
  let disabled = tagForm.find(':input:disabled').removeAttr('disabled');
  let TagData = tagForm.serializeArray();
  disabled.attr('disabled', 'disabled');

  let TagMap = {};
  $(TagData).each(async function (index, obj) {
    TagMap[obj.name] = obj.value;
  });
  let postData = [];

  $.each(TagMap, function (k, v) {
    if (k.startsWith("newtag_")) {
      let value_key = k.replace("newtag_", "newtagvalue_");
      let value = TagMap[value_key];
      postData.push({'type': "update_tag", 'name': v, 'value': value});
    } else if (k.startsWith("existingtag_")) {
      let value_key = k.replace("existingtag_", "existingtagvalue_");
      let oldvalue_key = k.replace("existingtag_", "existingtagoldvalue_");
      let value = TagMap[value_key];
      let oldvalue = TagMap[oldvalue_key];

      if (oldvalue !== value) {
        postData.push({'type': "update_tag", 'name': v, 'value': value});
      }
    }
  });
  if (postData.length === 0) {
    alert("No new tags were defined")
    return false;
  }
  let json = JSON.stringify(postData);
  let dimmer = $('.ui.dimmer');
  dimmer.addClass('active');
  let res = await sendRequestCommon(json);
  dimmer.removeClass('active');
  await handleResponse(res);
}

export async function addTagField() {
  let name = "tag" + tagInt;
  let new_tag = '<div class="fields" id="' + name + 'div">\n' +
    '                    <div class="field" >\n' +
    '                        <label>Tag name</label>\n' +
    '                        <input type="text" placeholder="Name" name="newtag_' + name + '" value="nflxtag-" id="' + name + '" value="nflxtag-">\n' +
    '                    </div>\n' +
    '                    <div class="field">\n' +
    '                        <label>Tag value</label>\n' +
    '                        <input type="text" placeholder="Value" name="newtagvalue_' + name + '" id="' + name + '_value">\n' +
    '                    </div>\n' +
    '<div class="field"><button class="ui red button" style="margin: 23px;width: 150px;" type="button" onClick="$(\'#' + name + 'div\').remove();">' +
    'Cancel</button></div></div>';
  tagInt += 1;
  $("#new_tags").append(new_tag);
  await forceTagPrefix(name);
  await preventDuplicateTags();
}

export async function forceTagPrefix(name) {
  $("#" + name).keydown(function (e) {
    let oldvalue = $(this).val();
    let field = this;
    setTimeout(function () {
      if (field.value.indexOf('nflxtag-') !== 0) {
        $(field).val(oldvalue);
      }
    }, 1);
  });
}

export async function preventDuplicateTags() {
  $('#tagForm input[name^=newtag_]').on('keyup', function () {
    let $current = $(this);
    let $duplicate = false;

    $('input[name^="newtag_"]').each(function () {
      if ($(this).val() === $current.val() && $(this).attr('id') !== $current.attr('id')) {
        $duplicate = true;
      }

    });
    $('input[name^="existingtag_"]').each(function () {
      if ($(this).val() === $current.val() && $(this).attr('id') !== $current.attr('id')) {
        $duplicate = true;
      }

    });

    if ($duplicate === true) {
      $("#tagsavebutton").attr("disabled", "disabled");
      $("#tagwarning").removeAttr("style");
      $("#tagwarningmsg").text("You have duplicate keys.");

    } else {
      $("#tagsavebutton").removeAttr("disabled");
      $("#tagwarning").attr("style", "display: none;");
    }

  });
}

export async function createPolicy() {
  $('#new_policy').css('display', '');
  let button = $('.ui.positive.button');
  button.attr("disabled", "disabled");
}

export async function changeNewPolicyTemplate(templateDD){
  neweditor.setValue(permission_value[templateDD.value].policy);
  // We re-set the editor value to a JSON stringified version of the value to ensure it is indented properly,
  // Just in case the value provided by config was not already indented properly.
  neweditor.setValue(JSON.stringify(JSON.parse(neweditor.getSession().getValue()), null, 4));
}

export async function cancelNewPolicy() {
  $('#new_policy').css('display', 'none');
  $('#new_policy_wizard').css('display', 'none');
  let button = $('.ui.positive.button');
  button.removeAttr("disabled");
  ReactDOM.unmountComponentAtNode(document.getElementById("new_policy_wizard"))
}

$("#tagForm").submit(function (event) {
  event.preventDefault();
  return false;
});


export function renderIAMSelfServiceWizard() {
  $('#new_policy_wizard').css('display', '');
  ReactDOM.render(
    <Provider store={store}>
      <SelfServiceForm
        ref={(SelfServiceForm) => {window.SelfServiceForm = SelfServiceForm}}
        isHidden={false}
        arn={arn}
        account_id={account_id}
        onSubmit={() => {}}
      />
    </Provider>,
    document.getElementById("new_policy_wizard")
  );
  $('#create-policy-button').attr("disabled", "disabled");
  $('#wizard-policy-button').attr("disabled", "disabled");
}