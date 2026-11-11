import { describe, test, expect } from "vitest";
import { parseArgv } from "./argv";

describe("parseArgv", () => {
  test("splits simple space-separated args", () => {
    expect(parseArgv("--title hello --body world")).toEqual(["--title", "hello", "--body", "world"]);
  });

  test("handles double-quoted values with spaces", () => {
    expect(parseArgv('--title "my note" --body "text body"')).toEqual(["--title", "my note", "--body", "text body"]);
  });

  test("handles single-quoted values with spaces", () => {
    expect(parseArgv("--title 'my note' --body 'text body'")).toEqual(["--title", "my note", "--body", "text body"]);
  });

  test("handles mixed quotes", () => {
    expect(parseArgv('--title "double quoted" --body \'single quoted\'')).toEqual(["--title", "double quoted", "--body", "single quoted"]);
  });

  test("handles empty input", () => {
    expect(parseArgv("")).toEqual([]);
    expect(parseArgv("   ")).toEqual([]);
  });

  test("handles escaped quotes inside double quotes", () => {
    expect(parseArgv('--title "hello \\"world\\""')).toEqual(["--title", 'hello "world"']);
  });

  test("handles escaped quotes inside single quotes", () => {
    expect(parseArgv("--title 'hello \\'world\\''")).toEqual(["--title", "hello 'world'"]);
  });

  test("handles backslash escapes", () => {
    expect(parseArgv("--title\\thello\\tworld")).toEqual(["--title", "hello", "world"]);
  });

  test("preserves special characters in quoted strings", () => {
    expect(parseArgv('--title "hello, world!"')).toEqual(["--title", "hello, world!"]);
  });

  test("handles flags with equals sign", () => {
    expect(parseArgv("--title=hello")).toEqual(["--title=hello"]);
  });

  test("handles quoted equals sign", () => {
    expect(parseArgv('--title="hello world"')).toEqual(["--title=hello world"]);
  });
});
