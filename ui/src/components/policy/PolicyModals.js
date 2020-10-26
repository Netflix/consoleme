import React, { useState } from "react";
import {
    Button,
    Dimmer,
    Form,
    Loader,
    Message,
    Modal,
    Segment,
    TextArea,
} from "semantic-ui-react";
import ReactMarkdown from "react-markdown";

const StatusMessage = ({ message, isSuccess }) => {
    if (message && isSuccess) {
        return (
            <Message positive>
                <Message.Header>Success</Message.Header>
                <Message.Content>
                    <ReactMarkdown linkTarget="_blank" source={message} />
                </Message.Content>
            </Message>
        );
    } else if (message && !isSuccess) {
        return (
            <Message negative>
                <Message.Header>Oops! There was a problem.</Message.Header>
                <Message.Content>
                    <ReactMarkdown linkTarget="_blank" source={message} />
                </Message.Content>
            </Message>
        );
    } else {
        return null;
    }
};

export const JustificationModal = (props) => {
    const {
        justification,
        setJustification,
        openJustification,
        setOpenJustification,
        removePolicy,
        handleSubmit,
    } = props;

    const [isLoading, setIsLoading] = useState(false);
    const [isSuccess, setIsSuccess] = useState(false);
    const [message, setMessage] = useState("");

    const handleJustificationUpdate = (e) => {
        setJustification(e.target.value);
    };

    const handleJustificationSubmit = async () => {
        if (!justification) {
            setMessage("No empty justification is allowed.");
            setIsSuccess(false);
            return
        }
        setIsLoading(true);
        const { message, request_created } = await handleSubmit();
        setMessage(message);
        setIsLoading(false);
        setIsSuccess(request_created);
        setJustification("");
    };

    const handleOk = () => {
        setMessage("");
        setIsSuccess(false);
        setJustification("");
        setOpenJustification(false);
    }

    const handleCancel = () => {
        setMessage("");
        setIsSuccess(false);
        setJustification("");
        setOpenJustification(false);
        // TODO, revisit this logic by passing the policy explicitly
        removePolicy();
    }

    return (
        <Modal
            onClose={() => setOpenJustification(false)}
            onOpen={() => setOpenJustification(true)}
            open={openJustification}
            closeOnDimmerClick={false}
        >
            <Modal.Header>Please enter in your justification</Modal.Header>
            <Modal.Content>
                <Dimmer.Dimmable
                    dimmed={isLoading}
                >
                    <StatusMessage
                        isSuccess={isSuccess}
                        message={message}
                    />
                    {!isSuccess && (
                        <Form>
                            <TextArea
                                placeholder="Tell us why you need this change"
                                onChange={handleJustificationUpdate}
                                style={{width: "fluid"}}
                                defaultValue={justification}
                            />
                        </Form>
                    )}

                    <Dimmer
                        active={isLoading}
                        inverted
                    >
                        <Loader />
                    </Dimmer>
                </Dimmer.Dimmable>
            </Modal.Content>
            <Modal.Actions>
                {isSuccess
                    ? (
                        <Button
                            content="Ok"
                            labelPosition="left"
                            icon="arrow right"
                            onClick={handleOk}
                            positive
                            disabled={isLoading}
                        />
                    )
                    : (
                        <Button
                            content="Submit"
                            labelPosition="left"
                            icon="arrow right"
                            onClick={handleJustificationSubmit}
                            positive
                            disabled={isLoading}
                        />
                    )
                }
                <Button
                    content="Cancel"
                    onClick={handleCancel}
                    icon="cancel"
                    negative
                    disabled={isLoading}
                />
            </Modal.Actions>
        </Modal>
    );
};

export const DeleteResourceModel = ({ toggle, setToggle, resource }) => {
    return (
        <Modal
            onClose={() => setToggle(false)}
            onOpen={() => setToggle(true)}
            open={toggle}
        >
            <Modal.Header>
                Deleting the role {resource.name}
            </Modal.Header>
            <Modal.Content image>
                <Modal.Description>
                    <p>Are you sure to delete this role?</p>
                </Modal.Description>
            </Modal.Content>
            <Modal.Actions>
                <Button
                    content="Delete"
                    labelPosition="left"
                    icon="remove"
                    onClick={() => setToggle(false)}
                    negative
                />
                <Button
                    onClick={() => setToggle(false)}
                >
                    Cancel
                </Button>
            </Modal.Actions>
        </Modal>
    );
};
