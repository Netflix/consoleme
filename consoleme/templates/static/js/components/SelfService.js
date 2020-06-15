import React, {Component} from 'react';
import ReactDOM from 'react-dom';
import {
    Button,
    Icon,
    Message,
    Segment,
    Step,
} from 'semantic-ui-react';
import SelfServiceStep1 from './SelfServiceStep1';
import SelfServiceStep2 from './SelfServiceStep2';
import SelfServiceStep3 from './SelfServiceStep3';
import {
    SelfServiceStepEnum,
} from './SelfServiceEnums';


class SelfService extends Component {
    state = {
        currStep: SelfServiceStepEnum.STEP1,
        messages: null,
        permissions: [],
        role: null,
    };

    handleStepClick(dir) {
        const {currStep} = this.state;

        let nextStep = null;
        switch (currStep) {
            case SelfServiceStepEnum.STEP1:
                // TODO, change dir to ENUM
                if (dir === 'next' && this.state.role != null) {
                    nextStep = SelfServiceStepEnum.STEP2;
                } else {
                    return this.setState({
                        messages: "Please supply IAM role either from your application or your roles."
                    });
                }
                break;
            case SelfServiceStepEnum.STEP2:
                if (dir === 'next' && this.state.permissions.length > 0) {
                    nextStep = SelfServiceStepEnum.STEP3;
                } else if (dir === 'previous') {
                    nextStep = SelfServiceStepEnum.STEP1;
                } else {
                    return this.setState({
                        messages: "Please add policy."
                    });
                }
                break;
            case SelfServiceStepEnum.STEP3:
                if (dir === 'previous') {
                    nextStep = SelfServiceStepEnum.STEP2;
                }
                break;
            default:
                return this.setState({
                    messages: "Unknown Errors. Please reach out to #security-help",
                });
        }

        this.setState({
            currStep: nextStep,
            messages: null,
        });
    }

    handleRoleUpdate(role) {
        this.setState({role});
    }

    handlePermissionsUpdate(permissions) {
        this.setState({permissions});
    }

    getCurrentSelfServiceStep() {
        const {currStep} = this.state;

        let SelfServiceStep = null;
        switch (currStep) {
            case SelfServiceStepEnum.STEP1:
                SelfServiceStep = (
                    <SelfServiceStep1
                        role={this.state.role}
                        handleRoleUpdate={
                            this.handleRoleUpdate.bind(this)
                        }
                    />
                );
                break;
            case SelfServiceStepEnum.STEP2:
                SelfServiceStep = (
                    <SelfServiceStep2
                        role={this.state.role}
                        permissions={this.state.permissions}
                        handlePermissionsUpdate={
                            this.handlePermissionsUpdate.bind(this)
                        }
                    />
                );
                break;
            case SelfServiceStepEnum.STEP3:
                SelfServiceStep = (
                    <SelfServiceStep3
                        role={this.state.role}
                        permissions={this.state.permissions}
                    />
                );
                break;
            default:
                SelfServiceStep = <div />;
        }

        return SelfServiceStep;
    }

    render() {
        const {currStep, messages} = this.state;
        const SelfServiceStep = this.getCurrentSelfServiceStep();
        const messagesToShow = (messages != null)
            ? (
                <Message negative>
                    <Message.Header>
                        There are some missing parameters
                    </Message.Header>
                    <p>{messages}</p>
                </Message>
            )
            : null;

        return (
            <Segment basic>
                <Step.Group fluid>
                    <Step
                        active={currStep === SelfServiceStepEnum.STEP1}
                    >
                        <Icon name='search' />
                        <Step.Content>
                            <Step.Title>
                                Step 1.
                            </Step.Title>
                            <Step.Description>
                                Search and Select Resource
                            </Step.Description>
                        </Step.Content>
                    </Step>
                    <Step
                        active={currStep === SelfServiceStepEnum.STEP2}
                    >
                        <Icon name='search plus' />
                        <Step.Content>
                            <Step.Title>
                                Step 2.
                            </Step.Title>
                            <Step.Description>
                                Provide Permission Details
                            </Step.Description>
                        </Step.Content>
                    </Step>
                    <Step
                        active={currStep === SelfServiceStepEnum.STEP3}
                    >
                        <Icon name='handshake' />
                        <Step.Content>
                            <Step.Title>
                                Step 3.
                            </Step.Title>
                            <Step.Description>
                                Review and Submit
                            </Step.Description>
                        </Step.Content>
                    </Step>
                </Step.Group>
                {messagesToShow}
                {SelfServiceStep}
                <Button
                    disabled={currStep === SelfServiceStepEnum.STEP1}
                    floated='left'
                    primary
                    // TODO, change to ENUM
                    onClick={this.handleStepClick.bind(this, 'previous')}
                >
                    Previous
                </Button>
                <Button
                    disabled={currStep === SelfServiceStepEnum.STEP3}
                    floated='right'
                    primary
                    onClick={this.handleStepClick.bind(this, 'next')}
                >
                    Next
                </Button>
            </Segment>
        );
    }
}

export function renderIAMSelfServiceWizard() {
    ReactDOM.render(
        <SelfService />,
        document.getElementById("new_policy_wizard"),
    );
}

export default SelfService;
