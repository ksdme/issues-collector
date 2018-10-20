import json
import argparse
from os import environ
from multiprocessing import Pool

from IGitt.GitHub.GitHub import GitHub, GitHubToken

def get_github(token):
  return GitHub(GitHubToken(token))

def parse_config(config):
  return json.loads(config)

def get_repo_host(url):
  if url.startswith('https://github.com'):
    return 'github'

def harvest_issue(issue, repo_url=None):
  return {
    'repo_url': repo_url,
    'id': issue.number,
    'title': issue.title,
    'labels': list(issue.labels),
    'description': issue.description,
  }

def select_suitable(issues, keywords):
  labels, desc_keywords = keywords['labels'], keywords['desc']

  for issue in issues:
    norm_issue_labels = set(map(str.lower, issue["labels"]))
    norm_labels = set(map(str.lower, labels))

    if len(norm_issue_labels & norm_labels) > 0:
      yield issue
      break

    norm_keywords = set(map(str.lower, desc_keywords))
    norm_text = str.lower(issue["title"] + ' ' + issue["description"])
    norm_text = set(norm_text.split())

    if len(norm_keywords & norm_text) > 0:
      yield issue
      break

def main(github, config):
  all_repo_issues = {}

  for target in config['targets']:
    print('processing', target)

    try:
      if get_repo_host(target) == 'github':
        gh_repo_name = target[19:]    #TODO: Improve this
        gh_repo = github.get_repo(gh_repo_name)

        with Pool(processes=8) as pool:
          all_issues = pool.map(harvest_issue, gh_repo.issues)

        for issue in all_issues:
          issue['repo_url'] = target

        all_repo_issues[gh_repo_name] = {
          'all': all_issues,
          'suitable': list(select_suitable(
            all_issues, config['keywords'])),
        }
      else:
        print('could not determine host for:', target)
    except Exception as e:
      print(e)
      continue

  return all_repo_issues

if __name__ == '__main__':
  github = get_github(environ['GITHUB_TOKEN'])

  args_parser = argparse.ArgumentParser()
  args_parser.add_argument('out', help='output json file')
  args_parser.add_argument('--config', '-c', required=True, help='configuration file')
  args = args_parser.parse_args()

  with open(args.config) as fyle:
    config = parse_config(fyle.read())

  result = main(github, config)

  with open(args.out, 'w') as fyle:
    fyle.write(json.dumps(result))
