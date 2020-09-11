import React from "react";
import { reduxForm } from "redux-form";
import { connect } from "react-redux";
import AceEditor from "react-ace";
import { Form } from "semantic-ui-react";
import ace from "brace";
import "brace/ext/language_tools";
let langTools = ace.acequire("ace/ext/language_tools");
langTools.addCompleter(permissionCompleter);

const Permissions = {
  S3: {
    list: ["s3:ListBucket", "s3:ListBucketVersions"],
    get: [
      "s3:GetObject",
      "s3:GetObjectTagging",
      "s3:GetObjectVersion",
      "s3:GetObjectVersionTagging",
      "s3:GetObjectAcl",
      "s3:GetObjectVersionAcl",
    ],
    put: [
      "s3:PutObject",
      "s3:PutObjectTagging",
      "s3:PutObjectVersionTagging",
      "s3:ListMultipartUploadParts*",
      "s3:AbortMultipartUpload",
      "s3:RestoreObject",
    ],
    delete: [
      "s3:DeleteObject",
      "s3:DeleteObjectTagging",
      "s3:DeleteObjectVersion",
      "s3:DeleteObjectVersionTagging",
    ],
  },
  SQS: {
    get: ["sqs:GetQueueAttributes", "sqs:GetQueueUrl"],
    send: ["sqs:SendMessage"],
    receive: ["sqs:ReceiveMessage"],
    delete: ["sqs:DeleteMessage"],
    set: ["sqs:SetQueueAttributes"],
  },
  SNS: {
    get: ["sns:GetEndpointAttributes", "sns:GetTopicAttributes"],
    publish: ["sns:Publish"],
    subscribe: ["sns:Subscribe", "sns:ConfirmSubscription"],
    unsubscribe: ["sns:Unsubscribe"],
  },
  R53: {
    list: ["route53:listresourcerecordsets"],
    change: ["route53:changeresourcerecordsets"],
  },
  EC2: {
    volmount: [
      "ec2:attachvolume",
      "ec2:createvolume",
      "ec2:describelicenses",
      "ec2:describevolumes",
      "ec2:detachvolume",
      "ec2:reportinstancestatus",
      "ec2:resetsnapshotattribute",
    ],
  },
  RDS: {
    passrole: ["iam:PassRole"],
  },
  STS: {
    assumerole: ["sts:AssumeRole"],
  },
  SES: {
    sendemail: ["ses:SendEmail", "ses:SendRawEmail"],
  },
};

let ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";

function random_id() {
  let rtn = "";
  for (let i = 0; i < 8; i++) {
    rtn += ALPHABET.charAt(Math.floor(Math.random() * ALPHABET.length));
  }
  return rtn;
}

function generate_id() {
  return "ConsoleMe" + random_id();
}

function generate_temp_id(expiration_date) {
  return "temp_" + expiration_date + "_" + random_id();
}

function generatePolicy(choices, policy_sid, state) {
  if (state.policy_value != null) {
    return state.policy_value;
  }
  choices.policy_type = "InlinePolicy";
  let actions = [];
  let resources = [];
  let policy = {
    Statement: [
      {
        Action: [],
        Effect: "Allow",
        Resource: [],
        Sid: policy_sid,
      },
    ],
  };
  if (choices.choose === "S3") {
    const regions = ["us-west-2", "eu-west-2"]; // Internal-only construct
    let prefix = "/*";
    if (choices.prefix && !choices.prefix.endsWith("/*")) {
      prefix = `${choices.prefix}/*`;
    } else if (choices.prefix && choices.prefix.endsWith("/*")) {
      prefix = `${choices.prefix}`;
    }

    if (!prefix.startsWith("/")) {
      prefix = "/" + prefix;
    }

    if (choices.bucket.includes("arn:aws:s3:::") === true) {
      resources = [choices.bucket + prefix];
      resources.push(choices.bucket);
    } else {
      resources = ["arn:aws:s3:::" + choices.bucket + prefix];
      resources.push("arn:aws:s3:::" + choices.bucket);
    }

    if (choices.multiregion === true) {
      regions.forEach((region) => {
        const base = `arn:aws:s3:::${region}.${choices.bucket}`;
        resources.push(base, `${base}${choices.prefix}`);
      });
    }

    ["list", "get", "put", "delete"].forEach((action) => {
      if (choices[action] === true) {
        actions.push(...Permissions[choices.choose][action]);
      }
    });
  } else if (choices.choose === "SQS") {
    resources = [choices.queuearn];

    ["get", "send", "receive", "delete", "set"].forEach((action) => {
      if (choices[action] === true) {
        actions.push(...Permissions[choices.choose][action]);
      }
    });
  } else if (choices.choose === "SNS") {
    resources = [choices.topicarn];

    ["get", "publish", "subscribe", "unsubscribe"].forEach((action) => {
      if (choices[action] === true) {
        actions.push(...Permissions[choices.choose][action]);
      }
    });
  } else if (choices.choose === "STS") {
    resources = [choices.rolearn];
    choices.assumerole = true;

    ["assumerole"].forEach((action) => {
      if (choices[action] === true) {
        actions.push(...Permissions[choices.choose][action]);
      }
    });
  } else if (choices.choose === "R53") {
    resources.push("*");

    ["list", "change"].forEach((action) => {
      if (choices[action] === true) {
        actions.push(...Permissions[choices.choose][action]);
      }
    });
  } else if (choices.choose === "EC2") {
    resources.push("*");

    ["volmount"].forEach((action) => {
      if (choices[action] === true) {
        actions.push(...Permissions[choices.choose][action]);
      }
    });
  } else if (choices.choose === "RDS") {
    ["passrole"].forEach((action) => {
      if (choices[action] === true) {
        actions.push(...Permissions[choices.choose][action]);
      }
    });
    if (choices.passrole === true) {
      resources.push(
        "arn:aws:iam::" + account_id + ":role/rds-monitoring-role"
      );
    }
  } else if (choices.choose === "SES") {
    choices.sendemail = true;

    ["sendemail"].forEach((action) => {
      if (choices[action] === true) {
        actions.push(...Permissions[choices.choose][action]);
      }
    });

    resources = [ses_arn];
    policy.Statement[0].Condition = {
      StringLike: {
        "ses:FromAddress": choices.fromaddress,
      },
    };
  }
  actions = new Set(actions);
  resources = new Set(resources);
  policy.Statement[0].Action = [...actions];
  policy.Statement[0].Resource = [...resources];
  return JSON.stringify(policy, null, 2);
}

function WizardAceEditor(policy_value, choices) {
  let style = { width: "200%" };
  if (window.location.href.endsWith("self_service")) {
    style = { left: "-50%", width: "200%" };
  }
  return (
    <AceEditor
      mode="json"
      ref={React.createRef()}
      theme={editor_theme}
      editorProps={{ $blockScrolling: true }}
      value={policy_value}
      style={style}
      enableBasicAutocompletion={true}
      enableLiveAutocompletion={true}
    />
  );
}

let SelfServiceFormPage3 = (props) => {
  const {
    handleSubmit,
    pristine,
    previousPage,
    submitting,
    choices,
    state,
  } = props;
  let policy_name;
  let policy_sid;
  if (choices.is_temporary) {
    policy_name = generate_temp_id(choices.expiration_date);
  } else {
    policy_name = generate_id();
  }
  policy_sid = policy_name.replace(/[^0-9a-z]/gi, "");
  choices.policy_name = policy_name;
  choices.policy_sid = policy_sid;
  let policy_value = generatePolicy(choices, policy_sid, state);
  choices.wizard_policy_editor = WizardAceEditor(policy_value, choices);

  return (
    <Form onSubmit={handleSubmit}>
      <Form.Field>
        <div>
          Please modify the policy if needed, then click the "Submit" button
          when done.
        </div>
        <div>
          Reference the{" "}
          <a
            href="https://awspolicygen.s3.amazonaws.com/policygen.html"
            target="_blank"
          >
            AWS Policy Generator
          </a>{" "}
          if you need a more complex set of permissions.
        </div>
        <br />
        {choices.wizard_policy_editor}
      </Form.Field>
      <Form.Field>
        <input
          type="hidden"
          id="policy_sid"
          name="policy_sid"
          value={policy_sid}
        ></input>
      </Form.Field>
      <button
        type="button"
        className="ui positive button previous"
        onClick={previousPage}
        style={{ margin: "10px" }}
      >
        Previous
      </button>
      <button
        type="submit"
        className="ui positive button submit"
        disabled={pristine || submitting}
        style={{ margin: "10px" }}
      >
        Submit
      </button>
    </Form>
  );
};

const mapStateToProps = (state) => ({});
SelfServiceFormPage3 = connect(mapStateToProps)(SelfServiceFormPage3);

export default reduxForm({
  form: "wizard",
  destroyOnUnmount: false,
  forceUnregisterOnUnmount: true,
})(SelfServiceFormPage3);
