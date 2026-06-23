import { context, getOctokit } from "@actions/github";
import * as core from '@actions/core';

export type Context = typeof context;
export type Core = typeof core;
export type GitHub = ReturnType<typeof getOctokit>;

export type Config = {
  baseCoverageJson: string;
  prCoverageMarkdown: string;
  prCoverageJson: string;
	context: Context;
	core: Core;
	github: GitHub;
};
