import React, { createContext, useContext, useReducer } from "react";
import { useAuth } from "../../auth/AuthProviderDefault";

const initialNotificationsState = {
  notifications: [],
  unreadNotificationCount: 0,
  intervalHookCalled: false,
};

const NotificationsContext = createContext(initialNotificationsState);
export const useNotifications = () => useContext(NotificationsContext);

const reducer = (state, action) => {
  switch (action.type) {
    case "SET_NOTIFICATIONS": {
      const { notifications } = action;
      return {
        ...state,
        notifications,
      };
    }
    case "SET_UNREAD_NOTIFICATION_COUNT": {
      const { unreadNotificationCount } = action;
      return {
        ...state,
        unreadNotificationCount,
      };
    }
    case "SET_INTERVAL_HOOK_CALLED": {
      return {
        ...state,
        intervalHookCalled: true,
      };
    }
    default: {
      return state;
    }
  }
};

export const NotificationProvider = ({ children }) => {
  const [state, dispatch] = useReducer(reducer, initialNotificationsState);
  const { user, sendRequestCommon } = useAuth();

  async function getAndSetNotifications(user) {
    if (!user?.site_config?.notifications?.enabled) return;
    const result = await sendRequestCommon(
      null,
      "/api/v2/notifications",
      "get"
    );

    // TODO: Error Handling
    if (!result?.data?.unreadNotificationCount) return;
    setUnreadNotificationCount(result.data.unreadNotificationCount);
    if (result.data.unreadNotificationCount > 0) {
      setNotifications(result.data.notifications);
    }
  }

  const setNotifications = (notifications) => {
    dispatch({
      type: "SET_NOTIFICATIONS",
      notifications,
    });
  };

  const setUnreadNotificationCount = (unreadNotificationCount) => {
    dispatch({
      type: "SET_UNREAD_NOTIFICATION_COUNT",
      unreadNotificationCount,
    });
  };

  const setIntervalHookCalled = () => {
    dispatch({
      type: "SET_INTERVAL_HOOK_CALLED",
    });
  };

  const RetrieveNotificationsAtInterval = (interval) => {
    if (state.intervalHookCalled) {
      return;
    }
    setInterval(function () {
      getAndSetNotifications(user);
    }, interval * 1000);
    setIntervalHookCalled();
  };

  return (
    <NotificationsContext.Provider
      value={{
        ...state,
        RetrieveNotificationsAtInterval,
      }}
    >
      {children}
    </NotificationsContext.Provider>
  );
};
