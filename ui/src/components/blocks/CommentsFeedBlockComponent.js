import React, { Component } from "react";
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

class CommentsFeedBlockComponent extends Component {
  constructor(props) {
    super(props);
    this.state = {
      requestID: this.props.requestID,
      isLoading: false,
      commentText: "",
      messages: [],
    };
    this.handleCommentChange = this.handleCommentChange.bind(this);
    this.handleSubmitComment = this.handleSubmitComment.bind(this);
    this.reloadDataFromBackend = props.reloadDataFromBackend;
  }

  handleCommentChange(e) {
    this.setState({
      commentText: e.target.value,
    });
  }

  handleSubmitComment() {
    const { commentText, requestID } = this.state;
    return this.setState(
      {
        isLoading: true,
        messages: [],
      },
      async () => {
        const request = {
          modification_model: {
            command: "add_comment",
            comment_text: commentText,
          },
        };
        const response = await this.props.sendRequestCommon(
          request,
          "/api/v2/requests/" + requestID,
          "PUT"
        );

        if (!response) {
          return;
        }

        if (response.status === 403 || response.status === 400) {
          // Error occurred making the request
          this.setState({
            isLoading: false,
            messages: [response.message],
          });
          return;
        }
        this.reloadDataFromBackend();
        this.setState({
          isLoading: false,
          commentText: "",
          messages: [],
        });
      }
    );
  }

  render() {
    const { commentText, isLoading, messages } = this.state;
    const { comments } = this.props;
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
                  <Comment.Author as="text">
                    {comment.user_email}
                  </Comment.Author>
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
        onClick={this.handleSubmitComment}
      />
    );

    const commentInput = (
      <Input
        action={addCommentButton}
        placeholder="Add a new comment..."
        fluid
        icon="comment"
        iconPosition="left"
        onChange={this.handleCommentChange}
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
  }
}

export default CommentsFeedBlockComponent;
