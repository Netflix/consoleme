import React, { useContext } from "react";
import { initialAuthState } from "./AuthState";

const AuthContext = React.createContext(initialAuthState);

export const useAuth = () => useContext(AuthContext);

export default AuthContext;
