FROM node:18-bookworm-slim

WORKDIR /opt/app

COPY package.json ./
RUN npm install

COPY . .

EXPOSE 1340

CMD ["npm", "run", "develop"]
