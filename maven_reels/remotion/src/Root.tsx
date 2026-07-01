import React from "react";
import { Composition } from "remotion";
import { MavenReel, defaultProps, ReelProps } from "./MavenReel";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="MavenReel"
      component={MavenReel}
      durationInFrames={540}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={defaultProps}
      calculateMetadata={({ props }: { props: ReelProps }) => {
        const fps = props.fps ?? 30;
        return {
          durationInFrames: Math.max(1, Math.round((props.durationSeconds ?? 18) * fps)),
          fps,
          width: 1080,
          height: 1920,
        };
      }}
    />
  );
};
