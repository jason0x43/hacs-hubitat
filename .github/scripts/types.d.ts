import { context as ghContext, getOctokit } from "@actions/github";
import * as ghCore from '@actions/core';

declare global {
	const context: typeof ghContext;
	const core: typeof ghCore;
	const github: ReturnType<typeof getOctokit>;
}

export type Config = {
  baseCoverageJson: string;
  prCoverageMarkdown: string;
  prCoverageJson: string;
};
