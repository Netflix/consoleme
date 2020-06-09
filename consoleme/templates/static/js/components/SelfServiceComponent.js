import React, { Component } from 'react';
import SelfServiceComponentCustom from "./SelfServiceComponentCustom";
import SelfServiceComponentEC2 from "./SelfServiceComponentEC2";
import SelfServiceComponentRDS from "./SelfServiceComponentRDS";
import SelfServiceComponentRoute53 from "./SelfServiceComponentRoute53";
import SelfServiceComponentS3 from './SelfServiceComponentS3';
import SelfServiceComponentSQS from "./SelfServiceComponentSQS";

// TODO, move this to config file.
const DEFAULT_AWS_SERVICE = 's3';


class SelfServiceComponent extends Component {
    // TODO(heewonk), load available components via dynamic import using module name pattern.
    static components = {
        custom: SelfServiceComponentCustom,
        ec2: SelfServiceComponentEC2,
        rds: SelfServiceComponentRDS,
        route53: SelfServiceComponentRoute53,
        s3: SelfServiceComponentS3,
        sqs: SelfServiceComponentSQS,
    };

    componentDidMount() {
        // TODO(heewonk), retrieve a config from backed to figure which components to register.
    }

    render() {
        const Component = SelfServiceComponent.components[this.props.service || DEFAULT_AWS_SERVICE];
        return <Component {...this.props} />;
    }
}

export default SelfServiceComponent;