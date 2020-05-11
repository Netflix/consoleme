import React, {Component} from 'react';


class SelfServiceComponentSQS extends Component {
    static TYPE = 'sqs';
    static NAME = 'SQS Queue';

    state = {
    };

    componentDidMount() {
        // initialize a permission state
        this.props.updatePermission({
            type: SelfServiceComponentSQS.TYPE,
        });
    }

    render() {

        return (
            <p>
                Custom Fields
            </p>
        );
    }
}

export default SelfServiceComponentSQS;
