import React, { useState } from "react";
import {
  Button,
  Comment,
  Divider,
  Header,
  Icon,
  Input,
  Message,
  Segment,
} from "semantic-ui-react";
import { sendRequestCommon } from "../../helpers/utils";

const CommentsFeedBlockComponent = (props) => {
  const initialState = {
    requestID: props.requestID,
    isLoading: false,
    commentText: "",
    messages: [],
  };

  const [state, setState] = useState(initialState);

  const reloadDataFromBackend = props.reloadDataFromBackend;

  const handleCommentChange = (e) => {
    setState({
      ...state,
      commentText: e.target.value,
    });
  };

  const handleSubmitComment = () => {
    const { commentText, requestID } = state;
    setState({
      ...state,
      isLoading: true,
      messages: [],
    });
    const handleAsyncCall = async () => {
      const request = {
        modification_model: {
          command: "add_comment",
          comment_text: commentText,
        },
      };
      const response = await sendRequestCommon(
        request,
        "/api/v2/requests/" + requestID,
        "PUT"
      );
      if (response.status === 403 || response.status === 400) {
        // Error occurred making the request
        setState({
          ...state,
          isLoading: false,
          messages: [response.message],
        });
        return;
      }
      reloadDataFromBackend();
      setState({
        ...state,
        isLoading: false,
        commentText: "",
        messages: [],
      });
    };
    handleAsyncCall();
  };

  const { commentText, isLoading, messages } = state;
  const { comments } = props;
  const messagesToShow =
    messages != null && messages.length > 0 ? (
      <Message negative>
        <Message.Header>An error occurred</Message.Header>
        <Message.List>
          {messages.map((message) => (
            <Message.Item>{message}</Message.Item>
          ))}
        </Message.List>
      </Message>
    ) : null;

  const commentsContent =
    comments && comments.length > 0 ? (
      <Comment.Group>
        {comments.map((comment) => (
          <Comment>
            {comment.user && comment.user.photo_url ? (
              <Comment.Avatar src={comment.user.photo_url} />
            ) : (
              <Comment.Avatar src="/static/images/logos/sunglasses/1.png" />
            )}
            <Comment.Content>
              {comment.user && comment.user.details_url ? (
                <Comment.Author as="a">
                  <a
                    href={comment.user.details_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {comment.user_email}
                  </a>
                </Comment.Author>
              ) : (
                <Comment.Author as="text">{comment.user_email}</Comment.Author>
              )}
              <Comment.Metadata>
                <div>{new Date(comment.timestamp).toLocaleString()}</div>
              </Comment.Metadata>
              <Comment.Text>{comment.text}</Comment.Text>
              <Comment.Actions>
                <Comment.Action>
                  <Divider />
                </Comment.Action>
              </Comment.Actions>
            </Comment.Content>
          </Comment>
        ))}
      </Comment.Group>
    ) : null;

  const addCommentButton = (
    <Button
      content="Add comment"
      primary
      disabled={commentText === ""}
      onClick={() => handleSubmitComment()}
    />
  );

  const commentInput = (
    <Input
      action={addCommentButton}
      placeholder="Add a new comment..."
      fluid
      icon="comment"
      iconPosition="left"
      onChange={(e) => handleCommentChange(e)}
      loading={isLoading}
      value={commentText}
    />
  );

  return (
    <Segment>
      <Header size="medium">
        Comments <Icon name="comments" />
      </Header>
      {commentsContent}
      {messagesToShow}
      {commentInput}
    </Segment>
  );
};

export default CommentsFeedBlockComponent;
