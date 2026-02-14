from cloudaux.aws.sts import boto3_cached_conn
import botocore.exceptions

class AccessAnalyzer:
    """
    The Access Analyzer class that hosts the methods related to the Access Analyzer API.
    """
        
    def check_no_new_access(self, new_policy_document, existing_policy_document, policy_type):
        """
        The check_no_new_access method compares the new policy document with the 
        existing policy document and returns the result.

        Args:
            existing_policy_document (string): The existing base policy as source of the truth.
            new_policy_document (string): The requested policy document to be compared.
            policy_type (string): The policy type to be compared. Only "IDENTITY_POLICY" is supported at the moment.

        Raises:
            ce: Raises the botocore exception if any error occurs.

        Returns:
            string: Returns the result of the comparison. Either "FAIL" or "PASS".
        """
        try:
            client = boto3_cached_conn("accessanalyzer")

            if policy_type != "IDENTITY_POLICY":
                raise ValueError("Only Identity Policy is supported at the moment.")
            response = client.check_no_new_access(
                existingPolicyDocument=existing_policy_document,
                newPolicyDocument=new_policy_document,
                policyType=policy_type
            )
            return response["result"]
        except botocore.exceptions.ClientError as ce:
            raise ce
