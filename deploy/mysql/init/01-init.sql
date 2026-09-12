-- ShortLink 初始化(由 docker-entrypoint-initdb.d 自动执行)
-- 仅在首次启动、数据卷为空时生效

-- 字符集与排序规则
CREATE DATABASE IF NOT EXISTS `shortlink`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

-- 如果部署时 MYSQL_USER 与 root 不同,需要补充授权
-- ALTER USER 'shortlink'@'%' IDENTIFIED WITH mysql_native_password BY 'shortlink';
-- GRANT ALL PRIVILEGES ON `shortlink`.* TO 'shortlink'@'%';
-- FLUSH PRIVILEGES;
