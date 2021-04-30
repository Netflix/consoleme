import React from "react";
import { Header } from "semantic-ui-react";
import { ReadOnlyPolicyMonacoEditor } from "./PolicyMonacoEditor";

const PermissionsBoundary = () => {
  const mockData =
    // eslint-disable-next-line max-len
    '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"cloudtrail:GetTrail","Resource":"*"},{"Effect":"Allow","Action":["iam:Generate1234567890","iam:Get1234567890"],"Resource":"*"},{"Effect":"Allow","Action":["s3:GetObject","s3:ListBucket","s3:GetBucketLocation"],"Resource":["arn:aws:s3:::aws-cloudtrail-logs-0123456789-cloudtrail-abcdefg","arn:aws:s3:::aws-cloudtrail-logs-123-cloudtrail-abcdef/*"]}]}';

  return (
    <>
      <Header as="h2">
        Permissions Boundary
        <Header.Subheader>
          Lorem ipsum dolor sit amet, consectetur adipisicing elit. A aliquid
          assumenda commodi cum cupiditate, debitis deserunt eligendi eos fuga
          itaque nam pariatur quibusdam, quisquam. Atque cupiditate iure libero
          sunt. Facere.
        </Header.Subheader>
      </Header>
      <ReadOnlyPolicyMonacoEditor policy={JSON.parse(mockData)} />
    </>
  );
};

export default PermissionsBoundary;
