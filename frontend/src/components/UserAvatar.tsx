import React from "react";
import { getAvatarSrc } from "../utils/api";

interface UserAvatarProps {
  name: string;
  avatarUrl?: string | null;
  size?: "sm" | "md";
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

const UserAvatar: React.FC<UserAvatarProps> = ({ name, avatarUrl, size = "md" }) => {
  const src = getAvatarSrc(avatarUrl);
  return (
    <span className={`user-avatar user-avatar--${size}`} title={name} aria-label={name}>
      {src ? <img src={src} alt={name} /> : <span>{getInitials(name)}</span>}
    </span>
  );
};

export default UserAvatar;
