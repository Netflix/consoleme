import React, { Component } from 'react';
import SelfServiceComponentS3 from './SelfServiceComponentS3';
import SelfServiceComponentSQS from './SelfServiceComponentSQS';
import SelfServiceComponentCustom from './SelfServiceComponentCustom';

// TODO, move this to config file.
const DEFAULT_AWS_SERVICE = 's3';


class SelfServiceComponent extends Component {
    // TODO(heewonk), load available components via dynamic import using module name pattern.
    static components = {
        s3: SelfServiceComponentS3,
        sqs: SelfServiceComponentSQS,
        custom: SelfServiceComponentCustom,
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