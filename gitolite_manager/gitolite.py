import os, glob, tempfile, shutil, re


class Gitolite(object):

    def __init__(self, path='./gitolite-admin'):
        self._repo_path = path
        self._user_repo_config = path + "/conf/user_repos.conf"
        self._gitolite_config = path + "/conf/gitolite.conf"
        self._key_path = path + "/keydir/"

        self._slaves_string = None
        gitolite_admin_conf_file = open(self._gitolite_config, "r")
        for line in gitolite_admin_conf_file:
            if re.match("option mirror.slaves", line):
                self._slaves_string = line.split("=")[1]
                gitolite_admin_conf_file.close()
                break

        self._repo_data = self.__load_repo()

    def save_repo(self):
        self.__save_repo(self._repo_data)

    def addRepo(self, username, reponame, add_user=True):
        """
        Adds a new repo to gitolite.
        returns true iff successfully added repo to config
        """

        repo_data = self.__load_repo()

        repo = username + '/' + reponame
        if repo in repo_data:
            return False

        repo_data[repo] = []
        if add_user:
            repo_data[repo].append(( 'RW+', username ))

        self.__save_repo(repo_data)

        return True

    def addUserToRepo(self, username, reponame, user, permission):
        """
        Adds 'user' withth 'permission' to 'reponame' of 'username' to config
        returns true iff successfully added users permission
        """
        repo_data = self.__load_repo()

        repo = username + '/' + reponame
        if repo not in repo_data:
            return False

        for i, (_, existing_user) in enumerate(repo_data[repo]):
            if existing_user == user:
                repo_data[repo][i] = (permission, user)
                break
        else:
            repo_data[repo].append((permission, user))

        self.__save_repo(repo_data)

        return True

    def removeUserFromRepo(self, username, reponame, user):
        """
        Removes 'user' from 'reponame' of 'username' from config.
        """
        repo_data = self.__load_repo()

        repo = username + '/' + reponame
        if repo not in repo_data:
            return False

        to_remove = []
        for i, (_, existing_user) in enumerate(repo_data[repo]):
            if existing_user == user:
                to_remove.append(i)

        for i in to_remove:
            del repo_data[repo][i]

        self.__save_repo(repo_data)

        return True

    def rmRepo(self, username, reponame):
        """
        Removes a repo
        returns true iff successfully removed repo from config.
        """

        repo_data = self.__load_repo()

        repo = username + '/' + reponame

        if repo not in repo_data:
            return False

        del repo_data[repo]

        self.__save_repo(repo_data)

        return True

    def getRepos(self):
        return self.__load_repo()


    def addSSHKey(self, username, keyname, sshkey):

        key_file_name = self.__get_ssh_key_path(username, keyname)

        try:
            with open(key_file_name) as f:
                return False
        except IOError as e:
            pass

        new_key_file = open(key_file_name, 'w')
        new_key_file.write(sshkey)
        new_key_file.close()

        return True

    def rmSSHKey(self, username, keyname):

        key_file_name = self.__get_ssh_key_path(username, keyname)

        try:
            os.remove(key_file_name)
        except:
            return False

        return True

    def getSSHKeys(self):

        keys = glob.glob(self._key_path + '*@*.pub')

        key_data = {}

        for keyfile in keys:
            filename = os.path.basename(keyfile)[:-4]
            filename_split = filename.split('@',1)

            if len(filename_split) != 2:
                raise SyntaxError('Invalid key file name')

            username = filename_split[0].strip()
            keyname = filename_split[1].strip()

            if username not in key_data:
                key_data[username] = []

            key_data[username].append(keyname)

        return key_data

    def __get_ssh_key_path(self, username, keyname):
        return self._key_path + username + "@" + keyname + ".pub"

    def __load_repo(self):
        """
        Read gitolite config file
        """

        repo_data = {}

        #repo [username]/[reponame]
        # RW+ = [username]

        repo_file_content = open(self._user_repo_config, 'r')

        line = repo_file_content.readline().strip()
        repo = ''

        while line != '':

            if line == '\n':
                # Consume empty lines.
                line = repo_file_content.readline()
                continue

            if line.startswith('repo'):
                line_split = line.split(None, 1)
                if len(line_split) != 2:
                    raise SyntaxError('Invalid repository def.')
                repo = line_split[1].strip()
                repo_data[repo] = []
            elif line.startswith(' '):
                if repo == '':
                    raise SyntaxError('Missing repo def.')

                line_split = line.split('=', 1)
                if len(line_split) != 2:
                    raise SyntaxError('Invalid rule')

                perm = line_split[0].strip()
                user = line_split[1].strip()

                if repo not in repo_data:
                    repo_data[repo] = []

                repo_data[repo].append( ( perm, user) )
            elif line.startswith("option"):
                # Gitolite mirroring options
                if repo == '':
                    raise SyntaxError('Missing repo def.')
                else:
                    pass
            else:
                raise SyntaxError('Invalid line: ' + line)

            line = repo_file_content.readline()

        repo_file_content.close()

        return repo_data

    def __save_repo(self, repo_data):
        """
        Write gitolite config file
        """


        tmp_file = tempfile.NamedTemporaryFile('w')

        for reponame, permlist in repo_data.items():
            tmp_file.write('repo ' + reponame + '\n')
            for perm, user in permlist:
                tmp_file.write(" " + perm + " = " + user + '\n')

            # Adds mirroring options
            if self._slaves_string is not None:
                tmp_file.write('option mirror.master = gitolite-master\n')
                tmp_file.write('option mirror.slaves =' + self._slaves_string + '\n')

        tmp_file.flush()
        shutil.copyfile(tmp_file.name, self._user_repo_config)
        tmp_file.close()
