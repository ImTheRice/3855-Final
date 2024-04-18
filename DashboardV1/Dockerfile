# Use Node.js version 13.12.0 Alpine image as the base image
FROM node:13.12.0-alpine

# Set the working directory in the Docker container
WORKDIR /app

# Add `/app/node_modules/.bin` to $PATH for convenience
ENV PATH /app/node_modules/.bin:$PATH

# Copy the package.json and package-lock.json files into our working directory
COPY package.json ./
COPY package-lock.json ./

# Install app dependencies specified in package.json
RUN npm install

# Install react-scripts globally within the container
RUN npm install react-scripts@3.4.1 -g

# Copy the rest of your app's source code from your host to your image filesystem
COPY . ./

# Start the app using npm start
CMD ["npm", "start"]

